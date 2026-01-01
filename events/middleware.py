# events/middleware.py (Create this new file - OPTIONAL but recommended)
from django.shortcuts import redirect
from django.urls import reverse

class AdminAccessMiddleware:
    """
    Middleware to ensure only staff users can access admin pages
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of admin-only paths
        admin_paths = ['/scan/', '/dashboard/']
        
        # Check if current path requires admin access
        if any(request.path.startswith(path) for path in admin_paths):
            if not request.user.is_authenticated:
                return redirect('admin_login')
            elif not (request.user.is_staff or request.user.is_superuser):
                return redirect('admin_login')
        
        response = self.get_response(request)
        return response