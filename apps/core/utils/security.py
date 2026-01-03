"""
Security utilities for input validation and sanitization.
"""

import re
import html
import logging
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.core.validators import validate_email
import phonenumbers
from phonenumbers import NumberParseException

logger = logging.getLogger(__name__)


class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    # Regex patterns for validation
    PATTERNS = {
        'loan_number': r'^[A-Z]{2,3}\d{6,10}$',
        'account_number': r'^[A-Z]{2}\d{8,12}$',
        'phone_number': r'^\+?[1-9]\d{1,14}$',
        'national_id': r'^[A-Z0-9]{8,20}$',
        'alphanumeric': r'^[a-zA-Z0-9\s\-_\.]+$',
        'name': r'^[a-zA-Z\s\-\'\.]+$',
        'currency_code': r'^[A-Z]{3}$',
        'percentage': r'^\d{1,2}(\.\d{1,2})?$',
    }
    
    @classmethod
    def validate_loan_number(cls, value):
        """Validate loan number format."""
        if not value:
            raise ValidationError("Loan number is required")
        
        value = str(value).strip().upper()
        if not re.match(cls.PATTERNS['loan_number'], value):
            raise ValidationError(
                "Loan number must be in format: XX123456 (2-3 letters followed by 6-10 digits)"
            )
        return value
    
    @classmethod
    def validate_account_number(cls, value):
        """Validate account number format."""
        if not value:
            raise ValidationError("Account number is required")
        
        value = str(value).strip().upper()
        if not re.match(cls.PATTERNS['account_number'], value):
            raise ValidationError(
                "Account number must be in format: XX12345678 (2 letters followed by 8-12 digits)"
            )
        return value
    
    @classmethod
    def validate_phone_number(cls, value, country_code='TZ'):
        """Validate and format phone number."""
        if not value:
            raise ValidationError("Phone number is required")
        
        try:
            # Parse the phone number
            parsed = phonenumbers.parse(value, country_code)
            
            # Check if it's valid
            if not phonenumbers.is_valid_number(parsed):
                raise ValidationError("Invalid phone number")
            
            # Return in international format
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            
        except NumberParseException:
            raise ValidationError("Invalid phone number format")
    
    @classmethod
    def validate_national_id(cls, value):
        """Validate national ID format."""
        if not value:
            raise ValidationError("National ID is required")
        
        value = str(value).strip().upper()
        if not re.match(cls.PATTERNS['national_id'], value):
            raise ValidationError(
                "National ID must be 8-20 alphanumeric characters"
            )
        return value
    
    @classmethod
    def validate_name(cls, value):
        """Validate person name."""
        if not value:
            raise ValidationError("Name is required")
        
        value = str(value).strip()
        if len(value) < 2:
            raise ValidationError("Name must be at least 2 characters")
        
        if len(value) > 100:
            raise ValidationError("Name must be less than 100 characters")
        
        if not re.match(cls.PATTERNS['name'], value):
            raise ValidationError(
                "Name can only contain letters, spaces, hyphens, apostrophes, and periods"
            )
        return value.title()
    
    @classmethod
    def validate_amount(cls, value, min_amount=0, max_amount=None):
        """Validate monetary amount."""
        if value is None:
            raise ValidationError("Amount is required")
        
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid amount format")
        
        if amount < min_amount:
            raise ValidationError(f"Amount must be at least {min_amount}")
        
        if max_amount and amount > max_amount:
            raise ValidationError(f"Amount must not exceed {max_amount}")
        
        # Check decimal places (max 2)
        if amount.as_tuple().exponent < -2:
            raise ValidationError("Amount can have at most 2 decimal places")
        
        return amount
    
    @classmethod
    def validate_percentage(cls, value, min_percent=0, max_percent=100):
        """Validate percentage value."""
        if value is None:
            raise ValidationError("Percentage is required")
        
        try:
            percent = float(value)
        except (ValueError, TypeError):
            raise ValidationError("Invalid percentage format")
        
        if percent < min_percent:
            raise ValidationError(f"Percentage must be at least {min_percent}%")
        
        if percent > max_percent:
            raise ValidationError(f"Percentage must not exceed {max_percent}%")
        
        return percent
    
    @classmethod
    def validate_email_address(cls, value):
        """Validate email address."""
        if not value:
            return None  # Email is optional in most cases
        
        value = str(value).strip().lower()
        try:
            validate_email(value)
            return value
        except ValidationError:
            raise ValidationError("Invalid email address format")
    
    @classmethod
    def sanitize_text(cls, value, max_length=None):
        """Sanitize text input."""
        if not value:
            return ""
        
        # Convert to string and strip whitespace
        value = str(value).strip()
        
        # Remove HTML tags
        value = strip_tags(value)
        
        # Escape HTML entities
        value = html.escape(value)
        
        # Limit length if specified
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @classmethod
    def validate_date_range(cls, start_date, end_date):
        """Validate date range."""
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError("Start date must be before end date")
        return True
    
    @classmethod
    def validate_loan_duration(cls, duration_months):
        """Validate loan duration."""
        if not duration_months:
            raise ValidationError("Loan duration is required")
        
        try:
            duration = int(duration_months)
        except (ValueError, TypeError):
            raise ValidationError("Loan duration must be a number")
        
        if duration < 1:
            raise ValidationError("Loan duration must be at least 1 month")
        
        if duration > 120:  # 10 years max
            raise ValidationError("Loan duration cannot exceed 120 months")
        
        return duration
    
    @classmethod
    def validate_interest_rate(cls, rate):
        """Validate interest rate."""
        if rate is None:
            raise ValidationError("Interest rate is required")
        
        try:
            rate = float(rate)
        except (ValueError, TypeError):
            raise ValidationError("Interest rate must be a number")
        
        if rate < 0:
            raise ValidationError("Interest rate cannot be negative")
        
        if rate > 100:
            raise ValidationError("Interest rate cannot exceed 100%")
        
        return rate


class SecurityLogger:
    """Security event logging utility."""
    
    @staticmethod
    def log_login_attempt(username, ip_address, success=True):
        """Log login attempt."""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"LOGIN_{status}: User={username}, IP={ip_address}")
    
    @staticmethod
    def log_permission_denied(user, action, resource):
        """Log permission denied events."""
        logger.warning(f"PERMISSION_DENIED: User={user}, Action={action}, Resource={resource}")
    
    @staticmethod
    def log_data_access(user, model, action, object_id=None):
        """Log data access events."""
        logger.info(f"DATA_ACCESS: User={user}, Model={model}, Action={action}, ID={object_id}")
    
    @staticmethod
    def log_security_violation(user, violation_type, details):
        """Log security violations."""
        logger.critical(f"SECURITY_VIOLATION: User={user}, Type={violation_type}, Details={details}")
    
    @staticmethod
    def log_admin_action(user, action, target):
        """Log administrative actions."""
        logger.info(f"ADMIN_ACTION: User={user}, Action={action}, Target={target}")


def require_https(view_func):
    """Decorator to require HTTPS for sensitive views."""
    def wrapper(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return redirect(f"https://{request.get_host()}{request.get_full_path()}")
        return view_func(request, *args, **kwargs)
    return wrapper


def validate_csrf_token(request):
    """Additional CSRF token validation."""
    from django.middleware.csrf import get_token
    
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        token = request.META.get('HTTP_X_CSRFTOKEN') or request.POST.get('csrfmiddlewaretoken')
        expected_token = get_token(request)
        
        if not token or token != expected_token:
            logger.warning(f"CSRF token validation failed for user {request.user}")
            return False
    
    return True
