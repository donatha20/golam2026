"""
Comprehensive error handling and logging utilities.
"""

import logging
import traceback
import sys
from functools import wraps
from django.http import JsonResponse, HttpResponseServerError
from django.shortcuts import render
from django.conf import settings
from django.core.mail import mail_admins
from django.utils import timezone
from django.db import transaction
import json

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling utility."""
    
    ERROR_CODES = {
        'VALIDATION_ERROR': 'E001',
        'DATABASE_ERROR': 'E002',
        'PERMISSION_DENIED': 'E003',
        'NOT_FOUND': 'E004',
        'BUSINESS_LOGIC_ERROR': 'E005',
        'EXTERNAL_SERVICE_ERROR': 'E006',
        'SYSTEM_ERROR': 'E007',
    }
    
    @classmethod
    def handle_error(cls, error, request=None, context=None):
        """Handle errors with appropriate logging and response."""
        error_id = cls._generate_error_id()
        error_type = cls._classify_error(error)
        
        # Log the error
        cls._log_error(error, error_id, error_type, request, context)
        
        # Send notification for critical errors
        if error_type in ['DATABASE_ERROR', 'SYSTEM_ERROR']:
            cls._notify_admins(error, error_id, request)
        
        return {
            'error_id': error_id,
            'error_code': cls.ERROR_CODES.get(error_type, 'E999'),
            'error_type': error_type,
            'message': cls._get_user_friendly_message(error_type),
            'timestamp': timezone.now().isoformat(),
        }
    
    @classmethod
    def _generate_error_id(cls):
        """Generate unique error ID."""
        import uuid
        return str(uuid.uuid4())[:8].upper()
    
    @classmethod
    def _classify_error(cls, error):
        """Classify error type."""
        error_name = error.__class__.__name__
        
        if 'ValidationError' in error_name:
            return 'VALIDATION_ERROR'
        elif 'DatabaseError' in error_name or 'IntegrityError' in error_name:
            return 'DATABASE_ERROR'
        elif 'PermissionDenied' in error_name:
            return 'PERMISSION_DENIED'
        elif 'DoesNotExist' in error_name or 'Http404' in error_name:
            return 'NOT_FOUND'
        elif 'BusinessLogicError' in error_name:
            return 'BUSINESS_LOGIC_ERROR'
        else:
            return 'SYSTEM_ERROR'
    
    @classmethod
    def _log_error(cls, error, error_id, error_type, request, context):
        """Log error with full context."""
        log_data = {
            'error_id': error_id,
            'error_type': error_type,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': timezone.now().isoformat(),
        }
        
        if request:
            log_data.update({
                'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                'path': request.path,
                'method': request.method,
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            })
        
        if context:
            log_data['context'] = context
        
        logger.error(f"Error {error_id}: {json.dumps(log_data, indent=2)}")
    
    @classmethod
    def _notify_admins(cls, error, error_id, request):
        """Send email notification to admins for critical errors."""
        if not settings.DEBUG and settings.ADMINS:
            subject = f"Critical Error {error_id} in Microfinance System"
            
            message = f"""
            A critical error occurred in the microfinance system:
            
            Error ID: {error_id}
            Error: {str(error)}
            Time: {timezone.now()}
            
            """
            
            if request:
                message += f"""
                User: {request.user if hasattr(request, 'user') else 'Anonymous'}
                Path: {request.path}
                Method: {request.method}
                IP: {cls._get_client_ip(request)}
                """
            
            message += f"\nTraceback:\n{traceback.format_exc()}"
            
            try:
                mail_admins(subject, message, fail_silently=True)
            except Exception as e:
                logger.error(f"Failed to send admin notification: {e}")
    
    @classmethod
    def _get_client_ip(cls, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def _get_user_friendly_message(cls, error_type):
        """Get user-friendly error message."""
        messages = {
            'VALIDATION_ERROR': 'Please check your input and try again.',
            'DATABASE_ERROR': 'A database error occurred. Please try again later.',
            'PERMISSION_DENIED': 'You do not have permission to perform this action.',
            'NOT_FOUND': 'The requested resource was not found.',
            'BUSINESS_LOGIC_ERROR': 'This operation cannot be completed due to business rules.',
            'EXTERNAL_SERVICE_ERROR': 'An external service is temporarily unavailable.',
            'SYSTEM_ERROR': 'A system error occurred. Please contact support.',
        }
        return messages.get(error_type, 'An unexpected error occurred.')


def handle_exceptions(view_func):
    """Decorator to handle exceptions in views."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            error_info = ErrorHandler.handle_error(e, request)
            
            # Return appropriate response based on request type
            if request.headers.get('Accept') == 'application/json' or request.path.startswith('/api/'):
                return JsonResponse({
                    'success': False,
                    'error': error_info,
                }, status=500)
            else:
                return render(request, 'errors/500.html', {
                    'error_info': error_info,
                }, status=500)
    
    return wrapper


def handle_database_errors(func):
    """Decorator to handle database errors with rollback."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            with transaction.atomic():
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise
    
    return wrapper


class BusinessLogicError(Exception):
    """Custom exception for business logic errors."""
    
    def __init__(self, message, code=None, details=None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(Exception):
    """Custom validation error."""
    
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class PermissionDeniedError(Exception):
    """Custom permission denied error."""
    
    def __init__(self, message, required_permission=None):
        self.message = message
        self.required_permission = required_permission
        super().__init__(self.message)


class AuditLogger:
    """Audit logging utility for tracking important actions."""
    
    @staticmethod
    def log_user_action(user, action, resource, details=None):
        """Log user actions for audit trail."""
        audit_data = {
            'user': str(user),
            'action': action,
            'resource': resource,
            'timestamp': timezone.now().isoformat(),
            'details': details or {},
        }
        
        logger.info(f"AUDIT: {json.dumps(audit_data)}")
    
    @staticmethod
    def log_data_change(user, model, instance_id, action, changes=None):
        """Log data changes."""
        audit_data = {
            'user': str(user),
            'model': model,
            'instance_id': instance_id,
            'action': action,  # CREATE, UPDATE, DELETE
            'changes': changes or {},
            'timestamp': timezone.now().isoformat(),
        }
        
        logger.info(f"DATA_CHANGE: {json.dumps(audit_data)}")
    
    @staticmethod
    def log_financial_transaction(user, transaction_type, amount, account, details=None):
        """Log financial transactions."""
        audit_data = {
            'user': str(user),
            'transaction_type': transaction_type,
            'amount': str(amount),
            'account': account,
            'timestamp': timezone.now().isoformat(),
            'details': details or {},
        }
        
        logger.info(f"FINANCIAL_TRANSACTION: {json.dumps(audit_data)}")


class HealthChecker:
    """System health monitoring utility."""
    
    @staticmethod
    def check_database():
        """Check database connectivity."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @staticmethod
    def check_cache():
        """Check cache functionality."""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 30)
            result = cache.get('health_check')
            cache.delete('health_check')
            return result == 'ok'
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    @staticmethod
    def check_disk_space():
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_percent = (free / total) * 100
            
            if free_percent < 10:  # Less than 10% free
                logger.warning(f"Low disk space: {free_percent:.1f}% free")
                return False
            return True
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return False
    
    @classmethod
    def get_system_health(cls):
        """Get overall system health status."""
        checks = {
            'database': cls.check_database(),
            'cache': cls.check_cache(),
            'disk_space': cls.check_disk_space(),
        }
        
        overall_health = all(checks.values())
        
        return {
            'healthy': overall_health,
            'checks': checks,
            'timestamp': timezone.now().isoformat(),
        }
