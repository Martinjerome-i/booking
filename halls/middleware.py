import jwt
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Protected admin paths that require authentication
        self.protected_paths = [
            '/admin_dashboard/', 
            '/admin_booking/',
            '/admin_manage/'
        ]

    def __call__(self, request):
        path = request.path
        
        # Check if current path is a protected path
        is_protected = any(path.startswith(protected) for protected in self.protected_paths)
        
        if is_protected:
            # Check for JWT token
            token = request.COOKIES.get('jwt_token')
            
            if not token:
                return redirect('admin_login')
                
            try:
                # Verify token
                jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            except:
                return redirect('admin_login')
        
        response = self.get_response(request)
        return response