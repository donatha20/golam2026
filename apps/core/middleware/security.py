"""
Security middleware for the microfinance system.
"""

import logging
import time
from django.http import HttpResponseForbidden
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
import re

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses."""
    
    def process_response(self, request, response):
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), gyroscope=()'
        )
        
        # Remove server information
        if 'Server' in response:
            del response['Server']
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware to prevent abuse."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # Skip rate limiting for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        # Get client IP
        ip = self.get_client_ip(request)
        
        # Different limits for different endpoints
        if request.path.startswith('/login/'):
            return self.check_rate_limit(ip, 'login', 5, 300)  # 5 attempts per 5 minutes
        elif request.path.startswith('/api/'):
            return self.check_rate_limit(ip, 'api', 100, 60)   # 100 requests per minute
        else:
            return self.check_rate_limit(ip, 'general', 200, 60)  # 200 requests per minute
    
    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_rate_limit(self, ip, endpoint, limit, window):
        """Check if the request exceeds rate limits."""
        cache_key = f'rate_limit:{endpoint}:{ip}'
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= limit:
            logger.warning(f'Rate limit exceeded for {ip} on {endpoint}')
            return HttpResponseForbidden('Rate limit exceeded. Please try again later.')
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, window)
        return None


class SessionSecurityMiddleware(MiddlewareMixin):
    """Enhanced session security middleware."""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Check for session hijacking
            if self.detect_session_hijacking(request):
                logger.warning(f'Potential session hijacking detected for user {request.user.username}')
                logout(request)
                return redirect(reverse('login'))
            
            # Update last activity
            request.session['last_activity'] = time.time()
            
            # Check session timeout
            if self.is_session_expired(request):
                logout(request)
                return redirect(reverse('login'))
        
        return None
    
    def detect_session_hijacking(self, request):
        """Detect potential session hijacking."""
        # Check if IP address changed
        current_ip = self.get_client_ip(request)
        session_ip = request.session.get('ip_address')
        
        if session_ip and session_ip != current_ip:
            # Allow IP change for mobile users, but log it
            logger.info(f'IP address changed for user {request.user.username}: {session_ip} -> {current_ip}')
        
        # Store current IP
        request.session['ip_address'] = current_ip
        
        # Check User-Agent consistency
        current_ua = request.META.get('HTTP_USER_AGENT', '')
        session_ua = request.session.get('user_agent')
        
        if session_ua and session_ua != current_ua:
            return True
        
        request.session['user_agent'] = current_ua
        return False
    
    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_session_expired(self, request):
        """Check if session has expired due to inactivity."""
        last_activity = request.session.get('last_activity')
        if not last_activity:
            return False
        
        # Session timeout (default 30 minutes)
        timeout = getattr(settings, 'SESSION_TIMEOUT', 1800)
        return time.time() - last_activity > timeout


class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """Middleware to detect and prevent SQL injection attempts."""
    
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(--|#|/\*|\*/)",
        r"(\bUNION\s+SELECT\b)",
        r"(\bINTO\s+OUTFILE\b)",
        r"(\bLOAD_FILE\b)",
    ]
    
    def process_request(self, request):
        # Check GET parameters
        for key, value in request.GET.items():
            if self.contains_sql_injection(value):
                logger.critical(f'SQL injection attempt detected in GET parameter {key}: {value}')
                return HttpResponseForbidden('Malicious request detected')
        
        # Check POST parameters
        for key, value in request.POST.items():
            if isinstance(value, str) and self.contains_sql_injection(value):
                logger.critical(f'SQL injection attempt detected in POST parameter {key}: {value}')
                return HttpResponseForbidden('Malicious request detected')
        
        return None
    
    def contains_sql_injection(self, value):
        """Check if value contains SQL injection patterns."""
        if not isinstance(value, str):
            return False
        
        value_upper = value.upper()
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False


class AuditLogMiddleware(MiddlewareMixin):
    """Middleware to log important user actions for audit purposes."""
    
    SENSITIVE_PATHS = [
        '/admin/',
        '/loans/',
        '/borrowers/',
        '/savings/',
        '/financial-statements/',
    ]
    
    def process_response(self, request, response):
        # Only log authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Only log sensitive paths
        if not any(request.path.startswith(path) for path in self.SENSITIVE_PATHS):
            return response
        
        # Only log successful requests
        if response.status_code >= 400:
            return response
        
        # Log the action
        logger.info(
            f'User: {request.user.username}, '
            f'Action: {request.method} {request.path}, '
            f'IP: {self.get_client_ip(request)}, '
            f'Status: {response.status_code}'
        )
        
        return response
    
    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


