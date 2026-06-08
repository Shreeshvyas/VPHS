import threading
from .models import ActivityLog

_thread_locals = threading.local()

def get_current_request():
    return getattr(_thread_locals, 'request', None)

import json

def log_activity(user, action, details=None, request=None):
    """
    Helper function to manually log user activity.
    """
    if not request:
        request = get_current_request()
        
    ip_address = None
    user_agent = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
    ActivityLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        details=json.dumps(details or {})
    )

class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        
        # Log important POST modifications automatically if user is authenticated
        response = self.get_response(request)
        
        if request.user.is_authenticated and request.method == 'POST':
            path = request.path
            # Ignore some common read-like or noise posts
            if not any(x in path for x in ['/jsi18n/', '/admin/jsi18n/']):
                # Extract clean post parameters (excluding passwords/sensitive info)
                post_data = {k: v for k, v in request.POST.items() if 'password' not in k.lower() and 'csrf' not in k.lower()}
                log_activity(
                    user=request.user,
                    action=f"POST {path}",
                    details={'method': request.method, 'post_data': post_data, 'status_code': response.status_code},
                    request=request
                )
                
        # Clear thread local request
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
            
        return response
