from .models import AcademicSession

def academic_session_processor(request):
    """
    Context processor to fetch the current active academic session.
    """
    try:
        active_session = AcademicSession.objects.get(is_active=True)
    except AcademicSession.DoesNotExist:
        # Fallback to the latest session if none is marked active
        active_session = AcademicSession.objects.order_by('-start_date').first()
    except AcademicSession.MultipleObjectsReturned:
        active_session = AcademicSession.objects.filter(is_active=True).first()

    return {
        'ACTIVE_SESSION': active_session,
        'ALL_SESSIONS': AcademicSession.objects.all()
    }
