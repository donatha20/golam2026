"""
Data tables for borrower management using Django Tables2.
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Borrower, BorrowerGroup, GroupMembership


class BorrowerTable(tables.Table):
    """Table for displaying borrowers with beautiful styling."""
    
    # Custom avatar column
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")
    
    # Borrower info columns
    full_name = tables.Column(empty_values=(), orderable=False, verbose_name="Name")
    borrower_id = tables.Column(verbose_name="ID")
    phone_number = tables.Column(verbose_name="Phone")
    
    # Personal details
    age = tables.Column(empty_values=(), orderable=False, verbose_name="Age")
    gender = tables.Column(verbose_name="Gender")
    occupation = tables.Column(verbose_name="Occupation")
    
    # Location and status
    location = tables.Column(empty_values=(), orderable=False, verbose_name="Location")
    status = tables.Column(empty_values=(), orderable=False, verbose_name="Status")
    
    # Registration details
    registration_date = tables.DateColumn(format="M d, Y", verbose_name="Registered")
    registered_by = tables.Column(empty_values=(), orderable=False, verbose_name="Officer")
    
    # Loan status
    loan_status = tables.Column(empty_values=(), orderable=False, verbose_name="Loan Status")
    
    # Actions column
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")
    
    class Meta:
        model = Borrower
        template_name = "django_tables2/bootstrap5.html"
        fields = ("avatar", "full_name", "borrower_id", "phone_number", "age", 
                 "gender", "occupation", "location", "status", "registration_date", 
                 "registered_by", "loan_status", "actions")
        attrs = {
            "class": "table table-hover borrower-table",
            "id": "borrower-table"
        }
    
    def render_avatar(self, record):
        """Render borrower avatar with initials."""
        initials = f"{record.first_name[:1]}{record.last_name[:1]}".upper()
        return format_html(
            '<div class="table-avatar">{}</div>',
            initials
        )
    
    def render_full_name(self, record):
        """Render full name with borrower ID."""
        nickname_html = ''
        if record.nickname:
            nickname_html = format_html(
                '<div class="borrower-id">Nickname: {}</div>',
                record.nickname,
            )

        return format_html(
            '<div class="borrower-name-cell">'
            '<div class="borrower-full-name">{}</div>'
            '<div class="borrower-id">{}</div>'
            '{}'
            '</div>',
            record.get_full_name(),
            record.borrower_id,
            nickname_html,
        )
    
    def render_age(self, record):
        """Render calculated age."""
        return f"{record.age} years"
    
    def render_gender(self, value):
        """Render gender with proper capitalization."""
        return value.title()
    
    def render_location(self, record):
        """Render location (ward, district)."""
        return f"{record.ward}, {record.district}"
    
    def render_status(self, record):
        """Render status with colored badge."""
        status_class = {
            'active': 'status-active',
            'suspended': 'status-suspended',
            'blacklisted': 'status-blacklisted',
            'inactive': 'status-inactive'
        }.get(record.status, 'status-inactive')
        
        return format_html(
            '<span class="status-badge {}">{}</span>',
            status_class,
            record.get_status_display()
        )
    
    def render_registered_by(self, record):
        """Render registered by officer name."""
        return record.registered_by.get_full_name()
    
    def render_loan_status(self, record):
        """Render current loan status."""
        can_take, reason = record.can_take_loan()
        if can_take:
            return mark_safe('<span class="text-success">Eligible</span>')
        elif "active loans" in reason.lower():
            return mark_safe('<span class="text-warning">Has Active Loan</span>')
        elif "defaulted" in reason.lower():
            return mark_safe('<span class="text-danger">Defaulted</span>')
        else:
            return mark_safe('<span class="text-muted">Not Eligible</span>')
    
    def render_actions(self, record):
        """Render action buttons."""
        return format_html(
            '<div class="action-buttons">'
            '<a href="{}" class="btn btn-sm btn-outline-primary" title="View Details">'
            '<i class="fas fa-eye"></i>'
            '</a>'
            '<a href="{}" class="btn btn-sm btn-outline-secondary ms-1" title="Edit Borrower">'
            '<i class="fas fa-edit"></i>'
            '</a>'
            '<a href="{}" class="btn btn-sm btn-outline-success ms-1" title="Add Loan">'
            '<i class="fas fa-plus"></i>'
            '</a>'
            '</div>',
            f'/borrowers/{record.id}/view/',
            f'/borrowers/{record.id}/edit/',
            f'/loans/add/?borrower={record.id}'
        )


class RegistrationReportTable(tables.Table):
    """Table for registration report."""
    
    # Borrower info
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")
    full_name = tables.Column(empty_values=(), orderable=False, verbose_name="Name")
    borrower_id = tables.Column(verbose_name="ID")
    
    # Personal details
    gender = tables.Column(verbose_name="Gender")
    age = tables.Column(empty_values=(), orderable=False, verbose_name="Age")
    occupation = tables.Column(verbose_name="Occupation")
    
    # Contact and location
    phone_number = tables.Column(verbose_name="Phone")
    location = tables.Column(empty_values=(), orderable=False, verbose_name="Location")
    
    # Registration details
    registration_date = tables.DateColumn(format="M d, Y", verbose_name="Registered")
    registered_by = tables.Column(empty_values=(), orderable=False, verbose_name="Officer")
    branch = tables.Column(empty_values=(), orderable=False, verbose_name="Branch")
    
    class Meta:
        model = Borrower
        template_name = "django_tables2/bootstrap5.html"
        fields = ("avatar", "full_name", "borrower_id", "gender", "age", 
                 "occupation", "phone_number", "location", "registration_date", 
                 "registered_by", "branch")
        attrs = {
            "class": "table table-hover registration-table",
            "id": "registration-table"
        }
    
    def render_avatar(self, record):
        """Render borrower avatar with initials."""
        initials = f"{record.first_name[:1]}{record.last_name[:1]}".upper()
        return format_html(
            '<div class="table-avatar-sm">{}</div>',
            initials
        )
    
    def render_full_name(self, record):
        """Render full name."""
        if record.nickname:
            return format_html(
                '{} <small class="text-muted">({})</small>',
                record.get_full_name(),
                record.nickname,
            )
        return record.get_full_name()
    
    def render_gender(self, value):
        """Render gender with icon."""
        icon = "fas fa-mars" if value == "male" else "fas fa-venus" if value == "female" else "fas fa-genderless"
        return format_html(
            '<i class="{}" style="margin-right: 0.5rem; color: #2b7a76;"></i>{}',
            icon, value.title()
        )
    
    def render_age(self, record):
        """Render calculated age."""
        return f"{record.age}"
    
    def render_location(self, record):
        """Render location."""
        return f"{record.ward}, {record.district}"
    
    def render_registered_by(self, record):
        """Render officer name."""
        return record.registered_by.get_full_name()
    
    def render_branch(self, record):
        """Render branch name."""
        return record.branch.name if record.branch else "N/A"


class BorrowerGroupTable(tables.Table):
    """Table for displaying borrower groups."""
    
    # Group info
    group_avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")
    group_name = tables.Column(verbose_name="Group Name")
    group_id = tables.Column(verbose_name="Group ID")
    
    # Leadership and members
    group_leader = tables.Column(empty_values=(), orderable=False, verbose_name="Leader")
    member_count = tables.Column(empty_values=(), orderable=False, verbose_name="Members")
    
    # Group details
    meeting_info = tables.Column(empty_values=(), orderable=False, verbose_name="Meetings")
    status = tables.Column(empty_values=(), orderable=False, verbose_name="Status")
    
    # Formation details
    formation_date = tables.DateColumn(format="M d, Y", verbose_name="Formed")
    registered_by = tables.Column(empty_values=(), orderable=False, verbose_name="Officer")
    
    # Loan status
    loan_status = tables.Column(empty_values=(), orderable=False, verbose_name="Loan Status")
    
    # Actions
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")
    
    class Meta:
        model = BorrowerGroup
        template_name = "django_tables2/bootstrap5.html"
        fields = ("group_avatar", "group_name", "group_id", "group_leader", 
                 "member_count", "meeting_info", "status", "formation_date", 
                 "registered_by", "loan_status", "actions")
        attrs = {
            "class": "table table-hover group-table",
            "id": "group-table"
        }
    
    def render_group_avatar(self, record):
        """Render group avatar with initials."""
        initials = "".join([word[:1] for word in record.group_name.split()[:2]]).upper()
        return format_html(
            '<div class="table-avatar group-avatar">{}</div>',
            initials
        )
    
    def render_group_leader(self, record):
        """Render group leader name."""
        return record.group_leader.get_full_name()
    
    def render_member_count(self, record):
        """Render member count with capacity."""
        count = record.member_count
        max_members = record.maximum_members
        percentage = (count / max_members * 100) if max_members > 0 else 0
        
        color = "#16a34a" if percentage < 80 else "#f59e0b" if percentage < 100 else "#ef4444"
        
        return format_html(
            '<div class="member-count">'
            '<span style="color: {}">{}/{}</span>'
            '<div class="member-progress">'
            '<div class="member-progress-bar" style="width: {}%; background: {};"></div>'
            '</div>'
            '</div>',
            color, count, max_members, percentage, color
        )
    
    def render_meeting_info(self, record):
        """Render meeting frequency and day."""
        frequency = record.get_meeting_frequency_display()
        day = record.get_meeting_day_display() if record.meeting_day else ""
        return f"{frequency}" + (f" ({day})" if day else "")
    
    def render_status(self, record):
        """Render status with colored badge."""
        status_class = {
            'active': 'status-active',
            'inactive': 'status-inactive',
            'suspended': 'status-suspended'
        }.get(record.status, 'status-inactive')
        
        return format_html(
            '<span class="status-badge {}">{}</span>',
            status_class,
            record.get_status_display()
        )
    
    def render_registered_by(self, record):
        """Render officer name."""
        return record.registered_by.get_full_name()
    
    def render_loan_status(self, record):
        """Render group loan eligibility."""
        if record.can_take_loan:
            return mark_safe('<span class="text-success">Eligible</span>')
        elif record.member_count < record.minimum_members:
            return mark_safe('<span class="text-warning">Need More Members</span>')
        elif record.active_group_loans > 0:
            return mark_safe('<span class="text-info">Has Active Loan</span>')
        else:
            return mark_safe('<span class="text-muted">Not Eligible</span>')
    
    def render_actions(self, record):
        """Render action buttons."""
        return format_html(
            '<div class="action-buttons">'
            '<button class="btn-action btn-view" title="View Group" data-id="{}">'
            '<i class="fas fa-eye"></i>'
            '</button>'
            '<button class="btn-action btn-members" title="Manage Members" data-id="{}">'
            '<i class="fas fa-users"></i>'
            '</button>'
            '<button class="btn-action btn-loan" title="Group Loan" data-id="{}">'
            '<i class="fas fa-money-bill-wave"></i>'
            '</button>'
            '</div>',
            record.id, record.id, record.id
        )


