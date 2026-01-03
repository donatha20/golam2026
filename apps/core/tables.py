"""
Data tables for the core app using Django Tables2.
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from apps.accounts.models import CustomUser, UserActivity, UserSession


class UserTable(tables.Table):
    """Table for displaying users with beautiful styling."""
    
    # Custom avatar column
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")
    
    # User info columns
    full_name = tables.Column(empty_values=(), orderable=False, verbose_name="Name")
    username = tables.Column(verbose_name="Username")
    email = tables.EmailColumn(verbose_name="Email")
    
    # Role and status with custom styling
    role = tables.Column(empty_values=(), orderable=False, verbose_name="Role")
    status = tables.Column(empty_values=(), orderable=False, verbose_name="Status")
    
    # Contact and dates
    phone_number = tables.Column(verbose_name="Phone", empty_values=())
    date_joined = tables.DateTimeColumn(format="M d, Y", verbose_name="Joined")
    last_login = tables.DateTimeColumn(format="M d, Y H:i", verbose_name="Last Login")
    
    # Actions column
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")
    
    class Meta:
        model = CustomUser
        template_name = "django_tables2/bootstrap5.html"
        fields = ("avatar", "full_name", "username", "email", "role", "status", 
                 "phone_number", "date_joined", "last_login", "actions")
        attrs = {
            "class": "table table-hover user-table",
            "id": "user-table"
        }
    
    def render_avatar(self, record):
        """Render user avatar with initials."""
        initials = f"{record.first_name[:1]}{record.last_name[:1]}".upper()
        return format_html(
            '<div class="table-avatar">{}</div>',
            initials
        )
    
    def render_full_name(self, record):
        """Render full name with username."""
        return format_html(
            '<div class="user-name-cell">'
            '<div class="user-full-name">{}</div>'
            '<div class="user-username">@{}</div>'
            '</div>',
            record.get_full_name(),
            record.username
        )
    
    def render_role(self, record):
        """Render role with badge styling."""
        return format_html(
            '<span class="role-badge">{}</span>',
            record.get_role_display()
        )
    
    def render_status(self, record):
        """Render status with colored badge."""
        status_class = "status-active" if record.is_active else "status-inactive"
        status_text = "Active" if record.is_active else "Inactive"
        return format_html(
            '<span class="status-badge {}">{}</span>',
            status_class,
            status_text
        )
    
    def render_phone_number(self, value):
        """Render phone number or placeholder."""
        return value if value else mark_safe('<span class="text-muted">Not provided</span>')
    
    def render_last_login(self, value):
        """Render last login or never."""
        if value:
            return value
        return mark_safe('<span class="text-muted">Never</span>')
    
    def render_actions(self, record):
        """Render action buttons."""
        return format_html(
            '<div class="action-buttons">'
            '<button class="btn-action btn-edit" title="Edit User">'
            '<i class="fas fa-edit"></i>'
            '</button>'
            '<button class="btn-action btn-delete" title="Delete User">'
            '<i class="fas fa-trash"></i>'
            '</button>'
            '</div>'
        )


class UserActivityTable(tables.Table):
    """Table for displaying user activities."""
    
    # User column with avatar
    user_info = tables.Column(empty_values=(), orderable=False, verbose_name="User")
    
    # Activity details
    action = tables.Column(verbose_name="Action")
    description = tables.Column(verbose_name="Description")
    ip_address = tables.Column(verbose_name="IP Address")
    timestamp = tables.DateTimeColumn(format="M d, H:i", verbose_name="Time")
    
    class Meta:
        model = UserActivity
        template_name = "django_tables2/bootstrap5.html"
        fields = ("user_info", "action", "description", "ip_address", "timestamp")
        attrs = {
            "class": "table table-hover activity-table",
            "id": "activity-table"
        }
    
    def render_user_info(self, record):
        """Render user info with avatar."""
        initials = f"{record.user.first_name[:1]}{record.user.last_name[:1]}".upper()
        return format_html(
            '<div class="user-activity-cell">'
            '<div class="table-avatar-sm">{}</div>'
            '<div class="user-activity-name">{}</div>'
            '</div>',
            initials,
            record.user.get_full_name()
        )
    
    def render_action(self, value):
        """Render action with styling."""
        return format_html(
            '<span class="action-badge">{}</span>',
            value.replace('_', ' ').title()
        )
    
    def render_description(self, value):
        """Render description with truncation."""
        if len(value) > 60:
            return format_html(
                '<span title="{}">{}</span>',
                value,
                value[:60] + '...'
            )
        return value


class UserSessionTable(tables.Table):
    """Table for displaying user sessions."""
    
    # User column with avatar
    user_info = tables.Column(empty_values=(), orderable=False, verbose_name="User")
    
    # Session details
    status = tables.Column(empty_values=(), orderable=False, verbose_name="Status")
    login_time = tables.DateTimeColumn(format="M d, H:i", verbose_name="Login")
    logout_time = tables.DateTimeColumn(format="M d, H:i", verbose_name="Logout")
    ip_address = tables.Column(verbose_name="IP Address")
    duration = tables.Column(empty_values=(), orderable=False, verbose_name="Duration")
    
    class Meta:
        model = UserSession
        template_name = "django_tables2/bootstrap5.html"
        fields = ("user_info", "status", "login_time", "logout_time", "ip_address", "duration")
        attrs = {
            "class": "table table-hover session-table",
            "id": "session-table"
        }
    
    def render_user_info(self, record):
        """Render user info with avatar."""
        initials = f"{record.user.first_name[:1]}{record.user.last_name[:1]}".upper()
        return format_html(
            '<div class="user-session-cell">'
            '<div class="table-avatar-sm">{}</div>'
            '<div class="user-session-name">{}</div>'
            '</div>',
            initials,
            record.user.get_full_name()
        )
    
    def render_status(self, record):
        """Render session status."""
        status_class = "session-active" if record.is_active else "session-ended"
        status_text = "Active" if record.is_active else "Ended"
        return format_html(
            '<span class="session-badge {}">{}</span>',
            status_class,
            status_text
        )
    
    def render_logout_time(self, value):
        """Render logout time or active indicator."""
        if value:
            return value
        return mark_safe('<span class="text-success">Still Active</span>')
    
    def render_duration(self, record):
        """Calculate and render session duration."""
        if record.logout_time:
            duration = record.logout_time - record.login_time
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"
        else:
            from django.utils import timezone
            duration = timezone.now() - record.login_time
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            return format_html(
                '<span class="text-success">{}</span>',
                f"{int(hours)}h {int(minutes)}m"
            )
