import io
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.http import HttpResponse, FileResponse, Http404
from django.utils.timezone import now

# ReportLab imports for professional PDF receipts
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from users.decorators import accountant_only, staff_only, principal_only
from users.middleware import log_activity
from academics.models import AcademicSession, ClassLevel
from students.models import Student, StudentEnrollment
from finance.models import CashBookEntry
from .models import FeeType, ClassFeeStructure, StudentFeeDiscount, StudentFeeStructure, FeeCollection, FeeCollectionItem
from .forms import FeeTypeForm, ClassFeeStructureForm, StudentFeeDiscountForm, FeeCollectionForm

# Helper to generate sequential receipt number
def generate_receipt_number():
    year = datetime.datetime.now().year
    last_collection = FeeCollection.all_objects.filter(receipt_number__startswith=f"RC-{year}-").order_by('-receipt_number').first()
    if last_collection:
        try:
            last_num = int(last_collection.receipt_number.split('-')[-1])
            new_num = last_num + 1
        except ValueError:
            new_num = 1
    else:
        new_num = 1
    return f"RC-{year}-{new_num:06d}"

# Fee Type CRUD
@login_required
@accountant_only
def fee_type_list(request):
    fee_types = FeeType.objects.all()
    if request.method == 'POST':
        form = FeeTypeForm(request.POST)
        if form.is_valid():
            ft = form.save()
            log_activity(request.user, "CREATE_FEE_TYPE", {"fee_type": ft.name})
            messages.success(request, f"Fee Type '{ft.name}' created successfully.")
            return redirect('fee_type_list')
    else:
        form = FeeTypeForm()
    return render(request, 'fees/fee_type_list.html', {'fee_types': fee_types, 'form': form})

@login_required
@accountant_only
def fee_type_delete(request, pk):
    ft = get_object_or_404(FeeType, pk=pk)
    if request.method == 'POST':
        ft.delete()
        log_activity(request.user, "DELETE_FEE_TYPE", {"fee_type": ft.name})
        messages.success(request, f"Fee Type '{ft.name}' deleted.")
        return redirect('fee_type_list')
    return render(request, 'academics/confirm_delete.html', {'obj': ft, 'title': 'Delete Fee Type'})

# Class Fee Structure CRUD
@login_required
@accountant_only
def class_fee_list(request):
    structures = ClassFeeStructure.objects.all().select_related('academic_session', 'class_level', 'fee_type')
    if request.method == 'POST':
        form = ClassFeeStructureForm(request.POST)
        if form.is_valid():
            cfs = form.save()
            log_activity(request.user, "CREATE_CLASS_FEE_STRUCTURE", {"class": cfs.class_level.name, "type": cfs.fee_type.name, "amount": str(cfs.amount)})
            messages.success(request, f"Fee Structure configured successfully.")
            return redirect('class_fee_list')
    else:
        form = ClassFeeStructureForm()
    return render(request, 'fees/class_fee_list.html', {'structures': structures, 'form': form})

@login_required
@accountant_only
def class_fee_delete(request, pk):
    cfs = get_object_or_404(ClassFeeStructure, pk=pk)
    if request.method == 'POST':
        cfs.delete()
        log_activity(request.user, "DELETE_CLASS_FEE_STRUCTURE", {"class": cfs.class_level.name, "type": cfs.fee_type.name})
        messages.success(request, f"Fee Structure deleted.")
        return redirect('class_fee_list')
    return render(request, 'academics/confirm_delete.html', {'obj': cfs, 'title': 'Delete Class Fee Structure'})

# Student Discounts
@login_required
@accountant_only
def student_discount_list(request):
    discounts = StudentFeeDiscount.objects.all().select_related('student', 'fee_type')
    if request.method == 'POST':
        form = StudentFeeDiscountForm(request.POST)
        if form.is_valid():
            disc = form.save()
            log_activity(request.user, "CREATE_STUDENT_DISCOUNT", {"student": disc.student.full_name, "type": disc.fee_type.name, "val": str(disc.value)})
            messages.success(request, f"Discount configured for {disc.student.full_name}.")
            return redirect('student_discount_list')
    else:
        form = StudentFeeDiscountForm()
    return render(request, 'fees/student_discount_list.html', {'discounts': discounts, 'form': form})

# Accountant Collection Dashboard
@login_required
@accountant_only
def fee_collection_dashboard(request):
    # Search is handled by UI which calls students.views.student_search_json
    return render(request, 'fees/collection_dashboard.html')

@login_required
@accountant_only
def collect_fee(request, enrollment_id):
    enrollment = get_object_or_404(StudentEnrollment, pk=enrollment_id, is_deleted=False)
    student = enrollment.student
    
    # Fetch all unpaid/partially paid structures
    dues = StudentFeeStructure.objects.filter(
        student_enrollment=enrollment,
        is_deleted=False
    ).exclude(status='PAID').order_by('due_date')
    
    # Calculate aggregates
    total_outstanding = sum(d.balance_amount for d in dues)
    
    if request.method == 'POST':
        form = FeeCollectionForm(request.POST)
        amount_paid_str = request.POST.get('amount_paid', '0')
        fine_applied_str = request.POST.get('fine_applied', '0')
        discount_applied_str = request.POST.get('discount_applied', '0')
        
        try:
            from decimal import Decimal
            amount_paid = Decimal(amount_paid_str)
            fine_applied = Decimal(fine_applied_str)
            discount_applied = Decimal(discount_applied_str)
        except (ValueError, TypeError):
            messages.error(request, "Invalid numeric values entered.")
            return redirect('collect_fee', enrollment_id=enrollment_id)
            
        if amount_paid <= 0:
            messages.error(request, "Amount paid must be greater than zero.")
        elif amount_paid > total_outstanding + fine_applied:
            messages.error(request, "Amount paid cannot exceed total outstanding dues + fines.")
        elif form.is_valid():
            with transaction.atomic():
                receipt_no = generate_receipt_number()
                
                collection = form.save(commit=False)
                collection.student_enrollment = enrollment
                collection.receipt_number = receipt_no
                collection.amount_paid = amount_paid
                collection.fine_applied = fine_applied
                collection.discount_applied = discount_applied
                collection.payment_date = now().date()
                collection.accountant = request.user
                collection.save()
                
                # Double-entry allocation loop
                remaining_payment = amount_paid
                
                for due in dues:
                    if remaining_payment <= 0:
                        break
                        
                    due_balance = due.balance_amount
                    
                    if remaining_payment >= due_balance:
                        # Fully pay this due item
                        due.paid_amount = due.net_amount
                        due.status = 'PAID'
                        due.save()
                        
                        FeeCollectionItem.objects.create(
                            fee_collection=collection,
                            student_fee_structure=due,
                            amount_allocated=due_balance
                        )
                        remaining_payment -= due_balance
                    else:
                        # Partially pay this due item
                        due.paid_amount = due.paid_amount + remaining_payment
                        due.status = 'PARTIALLY_PAID'
                        due.save()
                        
                        FeeCollectionItem.objects.create(
                            fee_collection=collection,
                            student_fee_structure=due,
                            amount_allocated=remaining_payment
                        )
                        remaining_payment = Decimal('0.00')
                
                # Auto-generate CashBookEntry
                # Non-cash payments mapped to BANK, cash to CASH
                pmode = 'BANK' if collection.payment_mode != 'CASH' else 'CASH'
                CashBookEntry.create_entry(
                    entry_date=collection.payment_date,
                    entry_type='DEBIT',
                    category='FEE_COLLECTION',
                    amount=collection.amount_paid,
                    payment_mode=pmode,
                    reference_id=receipt_no,
                    description=f"Fee collection from {student.full_name} ({student.admission_number})",
                    user=request.user
                )
                
            log_activity(request.user, "COLLECT_FEE", {"student": student.full_name, "receipt": receipt_no, "amount": amount_paid}, request)
            messages.success(request, f"Collected ₹{amount_paid:.2f} successfully. Receipt {receipt_no} generated.")
            return redirect('receipt_history')
    else:
        form = FeeCollectionForm()
        
    context = {
        'enrollment': enrollment,
        'student': student,
        'dues': dues,
        'total_outstanding': total_outstanding,
        'form': form
    }
    return render(request, 'fees/collect_fee.html', context)

# Receipt management
@login_required
@staff_only
def receipt_history(request):
    query = request.GET.get('q', '')
    collections = FeeCollection.objects.all().select_related('student_enrollment__student', 'student_enrollment__class_section__class_level', 'accountant')
    if query:
        collections = collections.filter(
            Q(receipt_number__icontains=query) |
            Q(student_enrollment__student__first_name__icontains=query) |
            Q(student_enrollment__student__last_name__icontains=query) |
            Q(student_enrollment__student__admission_number__icontains=query)
        )
    paginator = Paginator(collections, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'fees/receipt_history.html', {'page_obj': page_obj, 'query': query})

@login_required
@staff_only
def download_receipt_pdf(request, receipt_id):
    collection = get_object_or_404(FeeCollection, pk=receipt_id, is_deleted=False)
    enrollment = collection.student_enrollment
    student = enrollment.student
    
    # Check if duplicate download
    is_duplicate = request.GET.get('duplicate', '0') == '1'
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=20, alignment=1, textColor=colors.HexColor('#1E3A8A'))
    sub_title_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=9, alignment=1, textColor=colors.HexColor('#4A5568'))
    receipt_title = ParagraphStyle('RecTitle', parent=styles['Heading2'], fontSize=14, alignment=1, textColor=colors.HexColor('#B45309'), spaceAfter=15)
    body_style = ParagraphStyle('BodyText', parent=styles['Normal'], fontSize=9, leading=12)
    header_col_style = ParagraphStyle('HeadCol', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    
    elements = []
    
    # Duplicate watermark
    if is_duplicate:
        elements.append(Paragraph("DUPLICATE RECEIPT", ParagraphStyle('Watermark', parent=title_style, fontSize=12, textColor=colors.HexColor('#EF4444'))))
        elements.append(Spacer(1, 10))
        
    # Header
    elements.append(Paragraph("VYAS PUBLIC SCHOOL", title_style))
    elements.append(Paragraph("123 Education Way, Metropolis | Phone: +1-555-0199", sub_title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("PAYMENT RECEIPT", receipt_title))
    
    # Student and Transaction Info Table
    meta_data = [
        [Paragraph("Receipt No:", header_col_style), Paragraph(collection.receipt_number, body_style),
         Paragraph("Date:", header_col_style), Paragraph(str(collection.payment_date), body_style)],
        [Paragraph("Admission No:", header_col_style), Paragraph(student.admission_number, body_style),
         Paragraph("Class/Section:", header_col_style), Paragraph(str(enrollment.class_section), body_style)],
        [Paragraph("Student Name:", header_col_style), Paragraph(student.full_name, body_style),
         Paragraph("Academic Session:", header_col_style), Paragraph(enrollment.academic_session.name, body_style)],
        [Paragraph("Parent/Guardian:", header_col_style), Paragraph(student.guardian_name, body_style),
         Paragraph("Payment Mode:", header_col_style), Paragraph(collection.get_payment_mode_display(), body_style)]
    ]
    
    meta_table = Table(meta_data, colWidths=[1.25 * inch, 2.25 * inch, 1.25 * inch, 2.25 * inch])
    meta_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 20))
    
    # Allocation Table Headers
    allocated_items = collection.allocated_items.all().select_related('student_fee_structure__fee_type')
    table_data = [
        [Paragraph("S.No", header_col_style),
         Paragraph("Fee Component", header_col_style),
         Paragraph("Amount Paid (₹)", header_col_style)]
    ]
    
    for idx, item in enumerate(allocated_items, 1):
        table_data.append([
            Paragraph(str(idx), body_style),
            Paragraph(item.student_fee_structure.fee_type.name, body_style),
            Paragraph(f"{item.amount_allocated:.2f}", body_style)
        ])
        
    # Add summary rows
    table_data.append([Paragraph("", body_style), Paragraph("Fines Applied:", header_col_style), Paragraph(f"{collection.fine_applied:.2f}", body_style)])
    table_data.append([Paragraph("", body_style), Paragraph("Discounts Applied:", header_col_style), Paragraph(f"{collection.discount_applied:.2f}", body_style)])
    table_data.append([Paragraph("", body_style), Paragraph("Total Paid:", header_col_style), Paragraph(f"{collection.amount_paid:.2f}", body_style)])
    
    alloc_table = Table(table_data, colWidths=[0.75 * inch, 4.5 * inch, 1.75 * inch])
    alloc_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#1E3A8A')),
        ('LINEBELOW', (0,1), (-1,-4), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEABOVE', (1,-3), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    
    elements.append(alloc_table)
    elements.append(Spacer(1, 40))
    
    # Signatures
    sig_data = [
        [Paragraph(f"Received By: {collection.accountant.first_name if collection.accountant else 'System'}", body_style),
         Paragraph("Parent/Guardian Signature: _______________________", body_style)]
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    # Update reprint log
    log_activity(request.user, "REPRINT_RECEIPT", {"receipt_number": collection.receipt_number}, request)
    
    return FileResponse(buffer, as_attachment=False, filename=f"receipt_{collection.receipt_number}.pdf", content_type="application/pdf")

# Due Management
@login_required
@staff_only
def due_report(request):
    class_id = request.GET.get('class_level', '')
    
    try:
        active_session = AcademicSession.objects.get(is_active=True)
    except AcademicSession.DoesNotExist:
        active_session = AcademicSession.objects.order_by('-start_date').first()
        
    dues = StudentFeeStructure.objects.filter(is_deleted=False).exclude(status='PAID').select_related(
        'student_enrollment__student',
        'student_enrollment__class_section__class_level',
        'fee_type'
    )
    
    if active_session:
        dues = dues.filter(student_enrollment__academic_session=active_session)
        
    if class_id:
        dues = dues.filter(student_enrollment__class_section__class_level_id=class_id)
        
    # Aggregate by student enrollment to get total dues per student
    student_dues = {}
    for d in dues:
        en = d.student_enrollment
        if en.id not in student_dues:
            student_dues[en.id] = {
                'enrollment': en,
                'student': en.student,
                'class_section': en.class_section,
                'due_amount': 0.00
            }
        student_dues[en.id]['due_amount'] += float(d.balance_amount)
        
    context = {
        'student_dues': student_dues.values(),
        'class_levels': ClassLevel.objects.all(),
        'class_id': int(class_id) if class_id else None
    }
    return render(request, 'fees/due_report.html', context)

@login_required
@accountant_only
def send_due_reminder(request, enrollment_id):
    enrollment = get_object_or_404(StudentEnrollment, pk=enrollment_id, is_deleted=False)
    student = enrollment.student
    
    # Calculate unpaid dues
    unpaid = StudentFeeStructure.objects.filter(student_enrollment=enrollment, is_deleted=False).exclude(status='PAID')
    total_due = sum(d.balance_amount for d in unpaid)
    
    # Mock SMS/WhatsApp reminders
    log_activity(
        request.user,
        "SEND_DUE_REMINDER",
        {"student": student.full_name, "mobile": student.guardian_mobile, "amount_due": str(total_due)},
        request
    )
    messages.success(request, f"Mock SMS and WhatsApp due reminders dispatched to {student.guardian_name} ({student.guardian_mobile}) for ₹{total_due:.2f}.")
    return redirect('due_report')
