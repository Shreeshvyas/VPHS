import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse, FileResponse
from django.utils.timezone import now

# ReportLab imports for PDF ID Card
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from users.decorators import staff_only, admin_only
from users.middleware import log_activity
from academics.models import AcademicSession, ClassSection, ClassLevel
from .models import Student, StudentEnrollment, StudentHistory
from .forms import StudentForm, StudentEnrollmentForm

@login_required
@staff_only
def student_list(request):
    query = request.GET.get('q', '')
    class_section_id = request.GET.get('class_section', '')
    status_filter = request.GET.get('status', 'ACTIVE')
    
    # Fetch active academic session
    try:
        active_session = AcademicSession.objects.get(is_active=True)
    except AcademicSession.DoesNotExist:
        active_session = AcademicSession.objects.order_by('-start_date').first()
        
    enrollments = StudentEnrollment.objects.filter(is_deleted=False).select_related('student', 'class_section__class_level', 'class_section__section')
    
    if active_session:
        enrollments = enrollments.filter(academic_session=active_session)
        
    if query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__admission_number__icontains=query) |
            Q(student__father_name__icontains=query) |
            Q(roll_number__icontains=query)
        )
        
    if class_section_id:
        enrollments = enrollments.filter(class_section_id=class_section_id)
        
    if status_filter:
        enrollments = enrollments.filter(student__status=status_filter)
        
    paginator = Paginator(enrollments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'class_section_id': int(class_section_id) if class_section_id else None,
        'status_filter': status_filter,
        'class_sections': ClassSection.objects.filter(is_deleted=False).select_related('class_level', 'section'),
        'statuses': Student.STATUS_CHOICES
    }
    return render(request, 'students/student_list.html', context)

@login_required
@staff_only
def student_profile(request, pk):
    student = get_object_or_404(Student, pk=pk, is_deleted=False)
    enrollments = student.enrollments.filter(is_deleted=False).select_related('class_section__class_level', 'class_section__section', 'academic_session')
    history = student.history.all().select_related('academic_session', 'performed_by')
    
    # Import fees models to fetch balance/dues
    from fees.models import StudentFeeStructure
    fees_due = StudentFeeStructure.objects.filter(
        student_enrollment__student=student,
        is_deleted=False
    ).exclude(status='PAID').order_by('due_date')
    
    total_due = sum(f.net_amount - getattr(f, 'paid_amount', 0) for f in fees_due) # custom fallback handled in templates or view

    context = {
        'student': student,
        'enrollments': enrollments,
        'history': history,
        'fees_due': fees_due,
        'total_due': total_due
    }
    return render(request, 'students/student_profile.html', context)

@login_required
@staff_only
def student_create(request):
    if request.method == 'POST':
        student_form = StudentForm(request.POST, request.FILES)
        enrollment_form = StudentEnrollmentForm(request.POST)
        
        if student_form.is_valid() and enrollment_form.is_valid():
            with transaction.atomic():
                student = student_form.save()
                
                # Enroll student
                enrollment = enrollment_form.save(commit=False)
                enrollment.student = student
                
                # If roll number not provided, auto-assign
                if not enrollment.roll_number:
                    last_enrollment = StudentEnrollment.objects.filter(
                        academic_session=enrollment.academic_session,
                        class_section=enrollment.class_section,
                        is_deleted=False
                    ).order_by('-roll_number').first()
                    enrollment.roll_number = (last_enrollment.roll_number + 1) if (last_enrollment and last_enrollment.roll_number) else 1
                
                enrollment.save()
                
                # Create history log
                StudentHistory.objects.create(
                    student=student,
                    academic_session=enrollment.academic_session,
                    change_type='ADMISSION',
                    description=f"Admitted to {enrollment.class_section} for Session {enrollment.academic_session.name}",
                    performed_by=request.user
                )
                
                # Auto-initialize fee structure for the student based on class structure!
                from fees.models import ClassFeeStructure, StudentFeeStructure
                class_fees = ClassFeeStructure.objects.filter(
                    academic_session=enrollment.academic_session,
                    class_level=enrollment.class_section.class_level,
                    is_deleted=False
                )
                for cf in class_fees:
                    # Create student fee dues
                    # Calculate due_date based on session/month or current date.
                    # Simple rule: due date = cf.due_day_of_month of the current or next month
                    due_date = now().date() # simplified placeholder, can be configured dynamically
                    StudentFeeStructure.objects.create(
                        student_enrollment=enrollment,
                        fee_type=cf.fee_type,
                        original_amount=cf.amount,
                        discount_amount=0.00,
                        net_amount=cf.amount,
                        due_date=due_date,
                        status='UNPAID'
                    )
                
            log_activity(request.user, "STUDENT_ADMISSION", {"student": student.full_name, "admission_no": student.admission_number}, request)
            messages.success(request, f"Student {student.full_name} admitted successfully.")
            return redirect('student_profile', pk=student.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        student_form = StudentForm()
        enrollment_form = StudentEnrollmentForm()
        
    return render(request, 'students/student_form.html', {
        'student_form': student_form,
        'enrollment_form': enrollment_form,
        'title': 'New Student Admission'
    })

@login_required
@staff_only
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            log_activity(request.user, "STUDENT_UPDATE", {"student": student.full_name}, request)
            messages.success(request, f"Student {student.full_name} profile updated.")
            return redirect('student_profile', pk=student.pk)
        else:
            messages.error(request, "Please correct the errors.")
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/student_form.html', {'student_form': form, 'title': f"Edit Profile: {student.full_name}"})

@login_required
@admin_only
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk, is_deleted=False)
    if request.method == 'POST':
        with transaction.atomic():
            student.delete()
            # Soft delete associated enrollments
            StudentEnrollment.objects.filter(student=student).delete()
        log_activity(request.user, "STUDENT_DELETE", {"student": student.full_name}, request)
        messages.success(request, f"Student {student.full_name} soft-deleted from system.")
        return redirect('student_list')
    return render(request, 'students/student_confirm_delete.html', {'student': student})

@login_required
@staff_only
def student_search_json(request):
    """
    JSON API for autocomplete search of students.
    """
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
        
    try:
        active_session = AcademicSession.objects.get(is_active=True)
    except AcademicSession.DoesNotExist:
        active_session = AcademicSession.objects.order_by('-start_date').first()
        
    enrollments = StudentEnrollment.objects.filter(
        Q(student__first_name__icontains=query) |
        Q(student__last_name__icontains=query) |
        Q(student__admission_number__icontains=query),
        is_deleted=False
    ).select_related('student', 'class_section__class_level', 'class_section__section')
    
    if active_session:
        enrollments = enrollments.filter(academic_session=active_session)
        
    results = []
    for en in enrollments[:15]:
        results.append({
            'id': en.id,
            'student_id': en.student.id,
            'name': en.student.full_name,
            'admission_number': en.student.admission_number,
            'class_section': str(en.class_section),
            'roll_number': en.roll_number or '-'
        })
        
    return JsonResponse({'results': results})

@login_required
@staff_only
def student_id_card_pdf(request, pk):
    student = get_object_or_404(Student, pk=pk, is_deleted=False)
    
    # Get latest enrollment
    enrollment = student.enrollments.filter(is_deleted=False).select_related('class_section__class_level', 'class_section__section', 'academic_session').first()
    
    if not enrollment:
        raise Http404("Student is not currently enrolled in any class.")
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(3.375 * inch, 2.125 * inch),
                            rightMargin=5, leftMargin=5, topMargin=5, bottomMargin=5)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'SchoolTitle',
        parent=styles['Heading3'],
        fontSize=8,
        leading=9,
        textColor=colors.HexColor('#ffffff'),
        alignment=1 # Center
    )
    
    field_label_style = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontSize=6,
        leading=7,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#4A5568')
    )
    
    field_val_style = ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontSize=6,
        leading=7,
        fontName='Helvetica',
        textColor=colors.HexColor('#1A202C')
    )
    
    # Elements list
    elements = []
    
    # Header Table
    header_data = [[Paragraph("VYAS PUBLIC SCHOOL", title_style)]]
    header_table = Table(header_data, colWidths=[3.2 * inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    
    # Photo placeholder or student photo
    photo_width = 0.65 * inch
    photo_height = 0.75 * inch
    
    if student.photo and hasattr(student.photo, 'path'):
        try:
            # Create a reportlab image object from the file path
            photo_element = RLImage(student.photo.path, width=photo_width, height=photo_height)
        except Exception:
            photo_element = Paragraph("<b>NO PHOTO</b>", field_val_style)
    else:
        # Default placeholder box
        photo_element = Table([["PHOTO"]], colWidths=[photo_width], rowHeights=[photo_height])
        photo_element.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#E2E8F0')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ]))
        
    # Detail Table
    details_data = [
        [Paragraph("Name:", field_label_style), Paragraph(student.full_name, field_val_style)],
        [Paragraph("Adm No:", field_label_style), Paragraph(student.admission_number, field_val_style)],
        [Paragraph("Class:", field_label_style), Paragraph(str(enrollment.class_section), field_val_style)],
        [Paragraph("Roll No:", field_label_style), Paragraph(str(enrollment.roll_number or '-'), field_val_style)],
        [Paragraph("Guardian:", field_label_style), Paragraph(student.guardian_name, field_val_style)],
        [Paragraph("Mobile:", field_label_style), Paragraph(student.guardian_mobile, field_val_style)],
    ]
    
    details_table = Table(details_data, colWidths=[0.6 * inch, 1.7 * inch])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    
    # Main Body Layout (Photo on left, Details on right)
    body_data = [[photo_element, details_table]]
    body_table = Table(body_data, colWidths=[0.75 * inch, 2.4 * inch])
    body_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    elements.append(body_table)
    elements.append(Spacer(1, 3))
    
    # Footer Table
    footer_data = [[Paragraph("STUDENT IDENTITY CARD &bull; SESSION " + enrollment.academic_session.name, ParagraphStyle('FooterStyle', parent=field_label_style, fontSize=5, alignment=1, textColor=colors.HexColor('#ffffff')))]]
    footer_table = Table(footer_data, colWidths=[3.2 * inch])
    footer_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#D97706')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(footer_table)
    
    # Build Document
    doc.build(elements)
    
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, filename=f"id_card_{student.admission_number}.pdf", content_type="application/pdf")
