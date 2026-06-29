from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from users.decorators import admin_only, principal_only, staff_only
from users.middleware import log_activity
from .models import AcademicSession, ClassLevel, Section, ClassSection, Subject
from .forms import AcademicSessionForm, ClassLevelForm, SectionForm, ClassSectionForm, SubjectForm

# Lazy imports for student models to avoid circular imports
def get_student_enrollment_model():
    from students.models import StudentEnrollment
    return StudentEnrollment

def get_student_history_model():
    from students.models import StudentHistory
    return StudentHistory

@login_required
@principal_only
def session_list(request):
    sessions = AcademicSession.objects.all()
    if request.method == 'POST':
        form = AcademicSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            log_activity(request.user, "CREATE_SESSION", {"session": session.name})
            messages.success(request, f"Academic session {session.name} created successfully.")
            return redirect('session_list')
    else:
        form = AcademicSessionForm()
    return render(request, 'academics/session_list.html', {'sessions': sessions, 'form': form})

@login_required
@principal_only
def session_update(request, pk):
    session = get_object_or_404(AcademicSession, pk=pk)
    if request.method == 'POST':
        form = AcademicSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            log_activity(request.user, "UPDATE_SESSION", {"session": session.name})
            messages.success(request, f"Academic session {session.name} updated successfully.")
            return redirect('session_list')
    else:
        form = AcademicSessionForm(instance=session)
    return render(request, 'academics/session_form.html', {'form': form, 'session': session})

@login_required
@principal_only
def session_delete(request, pk):
    session = get_object_or_404(AcademicSession, pk=pk)
    if request.method == 'POST':
        session.delete()
        log_activity(request.user, "DELETE_SESSION", {"session": session.name})
        messages.success(request, f"Academic session {session.name} soft-deleted.")
        return redirect('session_list')
    return render(request, 'academics/confirm_delete.html', {'obj': session, 'title': 'Delete Session'})

# Class views
@login_required
@principal_only
def class_list(request):
    classes = ClassLevel.objects.all()
    if request.method == 'POST':
        form = ClassLevelForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            existing = ClassLevel.all_objects.filter(name__iexact=name).first()
            if existing:
                if existing.is_deleted:
                    existing.restore()
                    messages.success(request, f"Class {existing.name} (previously deleted) has been restored.")
                else:
                    messages.error(request, f"Class {existing.name} already exists.")
            else:
                cls = form.save()
                log_activity(request.user, "CREATE_CLASS", {"class": cls.name})
                messages.success(request, f"Class {cls.name} created successfully.")
            return redirect('class_list')
    else:
        form = ClassLevelForm()
    return render(request, 'academics/class_list.html', {'classes': classes, 'form': form})

@login_required
@principal_only
def class_delete(request, pk):
    cls = get_object_or_404(ClassLevel, pk=pk)
    if request.method == 'POST':
        cls.delete()
        log_activity(request.user, "DELETE_CLASS", {"class": cls.name})
        messages.success(request, f"Class {cls.name} soft-deleted.")
        return redirect('class_list')
    return render(request, 'academics/confirm_delete.html', {'obj': cls, 'title': 'Delete Class'})

# Section views
@login_required
@principal_only
def section_list(request):
    sections = Section.objects.all()
    if request.method == 'POST':
        form = SectionForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            existing = Section.all_objects.filter(name__iexact=name).first()
            if existing:
                if existing.is_deleted:
                    existing.restore()
                    messages.success(request, f"Section {existing.name} (previously deleted) has been restored.")
                else:
                    messages.error(request, f"Section {existing.name} already exists.")
            else:
                sec = form.save()
                log_activity(request.user, "CREATE_SECTION", {"section": sec.name})
                messages.success(request, f"Section {sec.name} created successfully.")
            return redirect('section_list')
    else:
        form = SectionForm()
    return render(request, 'academics/section_list.html', {'sections': sections, 'form': form})

@login_required
@principal_only
def section_delete(request, pk):
    sec = get_object_or_404(Section, pk=pk)
    if request.method == 'POST':
        sec.delete()
        log_activity(request.user, "DELETE_SECTION", {"section": sec.name})
        messages.success(request, f"Section {sec.name} soft-deleted.")
        return redirect('section_list')
    return render(request, 'academics/confirm_delete.html', {'obj': sec, 'title': 'Delete Section'})

# ClassSection views
@login_required
@principal_only
def class_section_list(request):
    class_sections = ClassSection.objects.all().select_related('class_level', 'section')
    if request.method == 'POST':
        form = ClassSectionForm(request.POST)
        if form.is_valid():
            class_level = form.cleaned_data.get('class_level')
            section = form.cleaned_data.get('section')
            existing = ClassSection.all_objects.filter(class_level=class_level, section=section).first()
            if existing:
                if existing.is_deleted:
                    existing.restore()
                    messages.success(request, f"Mapping {existing} (previously deleted) has been restored.")
                else:
                    messages.error(request, f"Mapping {existing} already exists.")
            else:
                cs = form.save()
                log_activity(request.user, "CREATE_CLASS_SECTION", {"class_section": str(cs)})
                messages.success(request, f"Mapping {cs} created successfully.")
            return redirect('class_section_list')
    else:
        form = ClassSectionForm()
    return render(request, 'academics/class_section_list.html', {'class_sections': class_sections, 'form': form})

@login_required
@principal_only
def class_section_delete(request, pk):
    cs = get_object_or_404(ClassSection, pk=pk)
    if request.method == 'POST':
        cs.delete()
        log_activity(request.user, "DELETE_CLASS_SECTION", {"class_section": str(cs)})
        messages.success(request, f"Mapping {cs} soft-deleted.")
        return redirect('class_section_list')
    return render(request, 'academics/confirm_delete.html', {'obj': cs, 'title': 'Delete Class Section Mapping'})

# Subject views
@login_required
@staff_only
def subject_list(request):
    subjects = Subject.objects.all().select_related('class_level')
    if request.method == 'POST':
        if not request.user.is_principal() and not request.user.is_super_admin():
            messages.error(request, "Only principal/admin can create subjects.")
            return redirect('subject_list')
        form = SubjectForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            class_level = form.cleaned_data.get('class_level')
            existing = Subject.all_objects.filter(name__iexact=name, class_level=class_level).first()
            if existing:
                if existing.is_deleted:
                    existing.restore()
                    messages.success(request, f"Subject {existing.name} (previously deleted) has been restored.")
                else:
                    messages.error(request, f"Subject {existing.name} already exists for this class.")
            else:
                sub = form.save()
                log_activity(request.user, "CREATE_SUBJECT", {"subject": sub.name, "class": sub.class_level.name})
                messages.success(request, f"Subject {sub.name} for {sub.class_level.name} created successfully.")
            return redirect('subject_list')
    else:
        form = SubjectForm()
    return render(request, 'academics/subject_list.html', {'subjects': subjects, 'form': form})

@login_required
@principal_only
def subject_delete(request, pk):
    sub = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        sub.delete()
        log_activity(request.user, "DELETE_SUBJECT", {"subject": sub.name})
        messages.success(request, f"Subject {sub.name} soft-deleted.")
        return redirect('subject_list')
    return render(request, 'academics/confirm_delete.html', {'obj': sub, 'title': 'Delete Subject'})

# Promotion Wizard
@login_required
@principal_only
def promotion_wizard(request):
    sessions = AcademicSession.objects.all()
    class_sections = ClassSection.objects.all().select_related('class_level', 'section')
    
    source_session_id = request.GET.get('source_session')
    source_class_section_id = request.GET.get('source_class_section')
    dest_session_id = request.GET.get('dest_session')
    dest_class_section_id = request.GET.get('dest_class_section')
    
    students_to_promote = []
    
    StudentEnrollment = get_student_enrollment_model()
    StudentHistory = get_student_history_model()
    
    if source_session_id and source_class_section_id:
        students_to_promote = StudentEnrollment.objects.filter(
            academic_session_id=source_session_id,
            class_section_id=source_class_section_id,
            is_deleted=False
        ).select_related('student')
        
    if request.method == 'POST':
        student_ids = request.POST.getlist('promote_students')
        dest_sess_id = request.POST.get('dest_session_post')
        dest_cs_id = request.POST.get('dest_class_section_post')
        
        if not student_ids:
            messages.error(request, "No students selected for promotion.")
        elif not dest_sess_id or not dest_cs_id:
            messages.error(request, "Please select destination session and class/section.")
        elif source_session_id == dest_sess_id:
            messages.error(request, "Source and destination sessions cannot be the same.")
        else:
            dest_session = get_object_or_404(AcademicSession, pk=dest_sess_id)
            dest_cs = get_object_or_404(ClassSection, pk=dest_cs_id)
            
            promoted_count = 0
            with transaction.atomic():
                for enrollment_id in student_ids:
                    enrollment = get_object_or_404(StudentEnrollment, pk=enrollment_id)
                    student = enrollment.student
                    
                    # Check if student is already enrolled in the destination session
                    already_enrolled = StudentEnrollment.objects.filter(
                        student=student,
                        academic_session=dest_session,
                        is_deleted=False
                    ).exists()
                    
                    if not already_enrolled:
                        # Find max roll number in dest class section
                        last_enrollment = StudentEnrollment.objects.filter(
                            academic_session=dest_session,
                            class_section=dest_cs,
                            is_deleted=False
                        ).order_by('-roll_number').first()
                        
                        next_roll = (last_enrollment.roll_number + 1) if (last_enrollment and last_enrollment.roll_number) else 1
                        
                        # Create new enrollment
                        StudentEnrollment.objects.create(
                            student=student,
                            academic_session=dest_session,
                            class_section=dest_cs,
                            roll_number=next_roll
                        )
                        
                        # Create history log
                        StudentHistory.objects.create(
                            student=student,
                            academic_session=dest_session,
                            change_type='PROMOTION',
                            description=f"Promoted from {enrollment.class_section} ({enrollment.academic_session.name}) to {dest_cs} ({dest_session.name})",
                            performed_by=request.user
                        )
                        promoted_count += 1
            
            messages.success(request, f"Successfully promoted {promoted_count} students to {dest_cs} for session {dest_session.name}.")
            return redirect('promotion_wizard')
            
    context = {
        'sessions': sessions,
        'class_sections': class_sections,
        'source_session_id': int(source_session_id) if source_session_id else None,
        'source_class_section_id': int(source_class_section_id) if source_class_section_id else None,
        'dest_session_id': int(dest_session_id) if dest_session_id else None,
        'dest_class_section_id': int(dest_class_section_id) if dest_class_section_id else None,
        'students_to_promote': students_to_promote
    }
    return render(request, 'academics/promotion_wizard.html', context)
