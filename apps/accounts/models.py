"""
User management models for the microfinance system.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from apps.core.models import TimeStampedModel


class UserRole(models.TextChoices):
    """User role choices."""
    ADMIN = 'admin', 'Administrator'
    LOAN_OFFICER = 'loan_officer', 'Loan Officer'


class Branch(TimeStampedModel):
    """
    Branch model to represent different branches/locations.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    address = models.TextField()
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    email = models.EmailField(blank=True, null=True)
    manager = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_branches'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Branches"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.LOAN_OFFICER
    )
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')],
        blank=True,
        null=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    profile_picture = models.ImageField(
        upload_to='user_profiles/',
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')],
        blank=True,
        null=True
    )
    hire_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    def get_full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def is_admin(self):
        """Check if user is an administrator."""
        return self.role == UserRole.ADMIN

    @property
    def is_loan_officer(self):
        """Check if user is a loan officer."""
        return self.role == UserRole.LOAN_OFFICER

    def can_manage_user(self, user):
        """Check if this user can manage another user."""
        if self.is_admin:
            return True
        return False

    def can_access_branch(self, branch):
        """Check if user can access a specific branch."""
        if self.is_admin:
            return True
        return self.branch == branch


class UserSession(models.Model):
    """
    Track user sessions for audit purposes.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class UserActivity(models.Model):
    """
    Log user activities for audit trail.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=100)
    description = models.TextField()
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Optional reference to related objects
    content_type = models.CharField(max_length=50, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "User Activities"

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
