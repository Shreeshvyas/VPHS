import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse, FileResponse, Http404
from django.utils.timezone import now

# ReportLab imports for professional PDF payslips
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from users.decorators import accountant_only, staff_only, principal_only, admin_only
from users.middleware import log_activity
from academics.models import AcademicSession
from finance.models import CashBookEntry
from .models import Staff, SalaryStructure, SalaryPayment
from .forms import StaffForm, SalaryStructureForm, SalaryPaymentForm

# Staff directory CRUD
@login_required
@staff_only
def staff_list(request):
    query = request.GET.get('q', '')
    dept_filter = request.GET.get('dept', '')
    
    staff_members = Staff.objects.filter(is_deleted=False)
    
    if query:
        staff_members = staff_members.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(employee_id__icontains=query) |
            Q(mobile__icontains=query)
        )
    if dept_filter:
        staff_members = staff_members.filter(department=dept_filter)
        
    paginator = Paginator(staff_members, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'dept_filter': dept_filter,
        'departments': Staff.DEPARTMENT_CHOICES
    }
    return render(request, 'staff/staff_list.html', context)

@login_required
@staff_only
def staff_profile(request, pk):
    staff = get_object_or_404(Staff, pk=pk, is_deleted=False)
    salary_history = staff.salaries.filter(is_deleted=False).order_by('-year', '-month')
    
    # Try fetching salary structure
    try:
        structure = staff.salary_structure
    except SalaryStructure.DoesNotExist:
        structure = None
        
    context = {
        'staff': staff,
        'salary_history': salary_history,
        'structure': structure
    }
    return render(request, 'staff/staff_profile.html', context)

@login_required
@admin_only
def staff_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                staff = form.save()
                # Automatically initialize default SalaryStructure
                SalaryStructure.objects.create(
                    staff=staff,
                    basic_salary=staff.base_salary,
                    allowance_default=0.00,
                    pf_deduction_default=0.00,
                    tax_deduction_default=0.00
                )
            log_activity(request.user, "CREATE_STAFF", {"name": staff.full_name, "id": staff.employee_id}, request)
            messages.success(request, f"Staff member {staff.full_name} registered successfully.")
            return redirect('staff_profile', pk=staff.pk)
    else:
        form = StaffForm()
    return render(request, 'staff/staff_form.html', {'form': form, 'title': 'Register New Employee'})

@login_required
@admin_only
def staff_update(request, pk):
    staff = get_object_or_404(Staff, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                # Update basic salary in structure if exists
                if hasattr(staff, 'salary_structure'):
                    struct = staff.salary_structure
                    struct.basic_salary = staff.base_salary
                    struct.save()
            log_activity(request.user, "UPDATE_STAFF", {"name": staff.full_name}, request)
            messages.success(request, f"Employee {staff.full_name} details updated.")
            return redirect('staff_profile', pk=staff.pk)
    else:
        form = StaffForm(instance=staff)
    return render(request, 'staff/staff_form.html', {'form': form, 'title': f"Edit Staff: {staff.full_name}"})

@login_required
@admin_only
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk, is_deleted=False)
    if request.method == 'POST':
        with transaction.atomic():
            staff.delete()
            # Soft delete salary structure
            SalaryStructure.objects.filter(staff=staff).delete()
        log_activity(request.user, "DELETE_STAFF", {"name": staff.full_name}, request)
        messages.success(request, f"Staff member {staff.full_name} soft-deleted.")
        return redirect('staff_list')
    return render(request, 'academics/confirm_delete.html', {'obj': staff, 'title': 'Delete Staff Profile'})

# Salary structures config
@login_required
@accountant_only
def edit_salary_structure(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id, is_deleted=False)
    structure, created = SalaryStructure.objects.get_or_create(
        staff=staff,
        defaults={'basic_salary': staff.base_salary}
    )
    
    if request.method == 'POST':
        form = SalaryStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            log_activity(request.user, "UPDATE_SALARY_STRUCTURE", {"staff": staff.full_name}, request)
            messages.success(request, f"Salary structure for {staff.full_name} updated.")
            return redirect('staff_profile', pk=staff.pk)
    else:
        form = SalaryStructureForm(instance=structure)
        
    return render(request, 'staff/structure_form.html', {'form': form, 'staff': staff})

# Payroll Dashboard & Process Scheduler
@login_required
@accountant_only
def salary_dashboard(request):
    month = request.GET.get('month', '')
    year = request.GET.get('year', '')
    
    payments = []
    if month and year:
        payments = SalaryPayment.objects.filter(month=month, year=year, is_deleted=False).select_related('staff')
        
    # Generate payroll action
    if request.method == 'POST' and 'generate_payroll' in request.POST:
        g_month = request.POST.get('gen_month')
        g_year = request.POST.get('gen_year')
        
        try:
            m_int = int(g_month)
            y_int = int(g_year)
        except ValueError:
            messages.error(request, "Invalid month or year selected.")
            return redirect('salary_dashboard')
            
        # Fetch active academic session
        try:
            active_session = AcademicSession.objects.get(is_active=True)
        except AcademicSession.DoesNotExist:
            active_session = AcademicSession.objects.order_by('-start_date').first()
            
        if not active_session:
            messages.error(request, "No active academic session found. Create a session first.")
            return redirect('salary_dashboard')
            
        active_staff = Staff.objects.filter(status='ACTIVE', is_deleted=False)
        created_count = 0
        
        with transaction.atomic():
            for staff in active_staff:
                # Check if payslip already exists
                exists = SalaryPayment.objects.filter(staff=staff, month=m_int, year=y_int, is_deleted=False).exists()
                if not exists:
                    # Get structure
                    struct, _ = SalaryStructure.objects.get_or_create(
                        staff=staff,
                        defaults={'basic_salary': staff.base_salary}
                    )
                    
                    net = struct.basic_salary + struct.allowance_default - struct.pf_deduction_default - struct.tax_deduction_default
                    payslip_no = f"SL-{y_int}{m_int:02d}-{staff.employee_id}"
                    
                    SalaryPayment.objects.create(
                        staff=staff,
                        academic_session=active_session,
                        month=m_int,
                        year=y_int,
                        base_salary=struct.basic_salary,
                        bonus=struct.allowance_default,
                        deductions=struct.pf_deduction_default + struct.tax_deduction_default,
                        net_salary=net,
                        payslip_number=payslip_no,
                        payment_status='PENDING'
                    )
                    created_count += 1
                    
        messages.success(request, f"Payroll processed: Generated {created_count} payslips for {m_int}/{y_int}.")
        return redirect(f"/salaries/?month={m_int}&year={y_int}")
        
    context = {
        'payments': payments,
        'month': month,
        'year': year,
        'months': range(1, 13)
    }
    return render(request, 'staff/salary_dashboard.html', context)

@login_required
@accountant_only
def pay_salary(request, payment_id):
    payment = get_object_or_404(SalaryPayment, pk=payment_id, is_deleted=False)
    staff = payment.staff
    
    if request.method == 'POST':
        form = SalaryPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            with transaction.atomic():
                pay = form.save(commit=False)
                # Recalculate net salary based on updated bonus/deductions
                pay.net_salary = pay.base_salary + pay.bonus - pay.deductions
                
                if pay.payment_status == 'PAID':
                    pay.payment_date = now().date()
                    pay.processed_by = request.user
                    pay.save()
                    
                    # Create cashbook out entry (CREDIT)
                    pmode = 'BANK' if pay.payment_mode != 'CASH' else 'CASH'
                    CashBookEntry.create_entry(
                        entry_date=pay.payment_date,
                        entry_type='CREDIT',
                        category='SALARY',
                        amount=pay.net_salary,
                        payment_mode=pmode,
                        reference_id=pay.payslip_number,
                        description=f"Salary paid to {staff.full_name} ({staff.employee_id}) for {pay.month}/{pay.year}",
                        user=request.user
                    )
                    messages.success(request, f"Salary payslip {pay.payslip_number} paid and logged in cashbook.")
                else:
                    pay.save()
                    messages.success(request, f"Payslip {pay.payslip_number} updated.")
                    
            log_activity(request.user, "PAY_SALARY", {"staff": staff.full_name, "payslip": pay.payslip_number, "net": str(pay.net_salary)}, request)
            return redirect(f"/salaries/?month={payment.month}&year={payment.year}")
    else:
        form = SalaryPaymentForm(instance=payment)
        
    context = {
        'form': form,
        'payment': payment,
        'staff': staff
    }
    return render(request, 'staff/pay_salary.html', context)

@login_required
@staff_only
def download_payslip_pdf(request, payment_id):
    payment = get_object_or_404(SalaryPayment, pk=payment_id, is_deleted=False)
    staff = payment.staff
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, alignment=1, textColor=colors.HexColor('#1E3A8A'))
    sub_title_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=9, alignment=1, textColor=colors.HexColor('#4A5568'))
    payslip_title = ParagraphStyle('SlipTitle', parent=styles['Heading2'], fontSize=12, alignment=1, textColor=colors.HexColor('#0F766E'), spaceAfter=15)
    body_style = ParagraphStyle('BodyText', parent=styles['Normal'], fontSize=9, leading=12)
    header_col_style = ParagraphStyle('HeadCol', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    
    elements = []
    
    # Header
    elements.append(Paragraph("VYAS PUBLIC SCHOOL", title_style))
    elements.append(Paragraph("123 Education Way, Metropolis | Payroll Department", sub_title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"SALARY PAYSLIP - {payment.month}/{payment.year}", payslip_title))
    
    # Staff details
    staff_data = [
        [Paragraph("Employee ID:", header_col_style), Paragraph(staff.employee_id, body_style),
         Paragraph("Payslip No:", header_col_style), Paragraph(payment.payslip_number, body_style)],
        [Paragraph("Staff Name:", header_col_style), Paragraph(staff.full_name, body_style),
         Paragraph("Department:", header_col_style), Paragraph(staff.get_department_display(), body_style)],
        [Paragraph("Designation:", header_col_style), Paragraph(staff.get_designation_display(), body_style),
         Paragraph("Status:", header_col_style), Paragraph(payment.get_payment_status_display(), body_style)],
        [Paragraph("Bank Name:", header_col_style), Paragraph(staff.bank_name or '-', body_style),
         Paragraph("Account Number:", header_col_style), Paragraph(staff.bank_account_number or '-', body_style)]
    ]
    
    staff_table = Table(staff_data, colWidths=[1.25 * inch, 2.25 * inch, 1.25 * inch, 2.25 * inch])
    staff_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(staff_table)
    elements.append(Spacer(1, 20))
    
    # Salary Breakup Table
    breakdown_data = [
        [Paragraph("Description", header_col_style), Paragraph("Earnings (₹)", header_col_style), Paragraph("Deductions (₹)", header_col_style)],
        [Paragraph("Basic Salary", body_style), Paragraph(f"{payment.base_salary:.2f}", body_style), Paragraph("0.00", body_style)],
        [Paragraph("Allowances / Bonus", body_style), Paragraph(f"{payment.bonus:.2f}", body_style), Paragraph("0.00", body_style)],
        [Paragraph("Deductions (Leaves/PF/Tax)", body_style), Paragraph("0.00", body_style), Paragraph(f"{payment.deductions:.2f}", body_style)],
        [Paragraph("Total", header_col_style), Paragraph(f"{payment.base_salary + payment.bonus:.2f}", header_col_style), Paragraph(f"{payment.deductions:.2f}", header_col_style)],
        [Paragraph("Net Salary Paid", header_col_style), Paragraph(f"{payment.net_salary:.2f}", header_col_style), Paragraph("", body_style)]
    ]
    
    breakdown_table = Table(breakdown_data, colWidths=[3.5 * inch, 1.75 * inch, 1.75 * inch])
    breakdown_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor('#0F766E')),
        ('LINEBELOW', (0,1), (-1,-3), 0.5, colors.HexColor('#E2E8F0')),
        ('LINEABOVE', (0,-2), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F0FDF4')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(breakdown_table)
    elements.append(Spacer(1, 40))
    
    # Footer and Signature
    sig_data = [
        [Paragraph("Paid By: _______________________", body_style),
         Paragraph("Employee Signature: _______________________", body_style)]
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return FileResponse(buffer, as_attachment=False, filename=f"payslip_{payment.payslip_number}.pdf", content_type="application/pdf")
