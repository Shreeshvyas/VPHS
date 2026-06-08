from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def role_required(*allowed_roles):
    """
    Decorator that checks if the logged-in user has one of the allowed roles.
    If not, raises PermissionDenied or redirects to a login/dashboard.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Super admins can access everything
            if request.user.is_superuser or request.user.role == 'SUPER_ADMIN':
                return view_func(request, *args, **kwargs)

            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            raise PermissionDenied("You do not have permission to access this resource.")
        return _wrapped_view
    return decorator

# Convenience decorators
def super_admin_only(view_func):
    return role_required('SUPER_ADMIN')(view_func)

def admin_only(view_func):
    return role_required('SUPER_ADMIN', 'SCHOOL_ADMIN')(view_func)

def accountant_only(view_func):
    return role_required('SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT')(view_func)

def principal_only(view_func):
    return role_required('SUPER_ADMIN', 'SCHOOL_ADMIN', 'PRINCIPAL')(view_func)

def teacher_only(view_func):
    return role_required('SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER')(view_func)

def staff_only(view_func):
    """Allows Super Admin, School Admin, Accountant, Principal, Teacher, Receptionist"""
    return role_required('SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'PRINCIPAL', 'TEACHER', 'RECEPTIONIST')(view_func)
