"""
Django tables for finance tracker app.
"""
import django_tables2 as tables
from django.utils.html import format_html
from django.urls import reverse
from .models import Income, Expenditure


class IncomeTable(tables.Table):
    """Table for displaying income records."""

    # Avatar column for visual consistency
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")
    
    # Income details
    income_id = tables.Column(verbose_name="Income ID")
    source = tables.Column(empty_values=(), verbose_name="Source")
    category = tables.Column(empty_values=(), verbose_name="Category")
    amount = tables.Column(verbose_name="Amount")
    income_date = tables.DateColumn(format="M d, Y", verbose_name="Date")
    
    # Additional info
    received_from = tables.Column(verbose_name="Received From")
    payment_method = tables.Column(verbose_name="Payment Method")
    recorded_by = tables.Column(empty_values=(), verbose_name="Recorded By")
    
    # Actions
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Income
        template_name = "django_tables2/bootstrap4.html"
        fields = ("avatar", "income_id", "source", "category", "amount", "income_date", 
                 "received_from", "payment_method", "recorded_by", "actions")
        attrs = {
            "class": "table table-hover income-table",
            "id": "income-table"
        }

    def render_avatar(self, record):
        """Render income avatar with source initial."""
        initial = record.get_source_display()[:1].upper()
        return format_html(
            '<div class="table-avatar income-avatar">{}</div>',
            initial
        )

    def render_source(self, record):
        """Render income source display name."""
        return record.get_source_display()

    def render_category(self, record):
        """Render category name or dash if none."""
        return record.category.name if record.category else "â€”"

    def render_amount(self, value):
        """Render amount with currency formatting."""
        return format_html(
            '<span class="amount-cell income-amount">Tsh {:,.2f}</span>',
            value or 0
        )

    def render_received_from(self, value):
        """Render received from or dash if empty."""
        return value or "â€”"

    def render_payment_method(self, value):
        """Render payment method or dash if empty."""
        return value or "â€”"

    def render_recorded_by(self, record):
        """Render recorded by user."""
        return record.recorded_by.get_full_name() if record.recorded_by else "â€”"

    def render_actions(self, record):
        """Render actions column."""
        return format_html(
            '<div class="action-buttons">'
            '<button class="btn-action btn-view" title="View Details" data-id="{}">'
            '<i class="fas fa-eye"></i></button>'
            '<button class="btn-action btn-edit" title="Edit Income" data-id="{}">'
            '<i class="fas fa-edit"></i></button>'
            '</div>',
            record.id,
            record.id
        )


class ExpenditureTable(tables.Table):
    """Table for displaying expenditure records."""

    # Avatar column for visual consistency
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")
    
    # Expenditure details
    expenditure_id = tables.Column(verbose_name="Expenditure ID")
    expenditure_type = tables.Column(empty_values=(), verbose_name="Type")
    category = tables.Column(empty_values=(), verbose_name="Category")
    amount = tables.Column(verbose_name="Amount")
    expenditure_date = tables.DateColumn(format="M d, Y", verbose_name="Date")
    
    # Vendor info
    vendor_name = tables.Column(verbose_name="Vendor")
    payment_method = tables.Column(verbose_name="Payment Method")
    
    # Status and tracking
    status = tables.Column(empty_values=(), verbose_name="Status")
    recorded_by = tables.Column(empty_values=(), verbose_name="Recorded By")
    
    # Actions
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Expenditure
        template_name = "django_tables2/bootstrap4.html"
        fields = ("avatar", "expenditure_id", "expenditure_type", "category", "amount", 
                 "expenditure_date", "vendor_name", "payment_method", "status", "recorded_by", "actions")
        attrs = {
            "class": "table table-hover expenditure-table",
            "id": "expenditure-table"
        }

    def render_avatar(self, record):
        """Render expenditure avatar with type initial."""
        initial = record.get_expenditure_type_display()[:1].upper()
        status_colors = {
            'pending': '#f59e0b',
            'approved': '#10b981',
            'paid': '#059669',
            'rejected': '#ef4444',
        }
        color = status_colors.get(record.status, '#6b7280')
        
        return format_html(
            '<div class="table-avatar expenditure-avatar" style="background-color: {}20; color: {}">{}</div>',
            color, color, initial
        )

    def render_expenditure_type(self, record):
        """Render expenditure type display name."""
        return record.get_expenditure_type_display()

    def render_category(self, record):
        """Render category name or dash if none."""
        return record.category.name if record.category else "â€”"

    def render_amount(self, value):
        """Render amount with currency formatting."""
        return format_html(
            '<span class="amount-cell expenditure-amount">Tsh {:,.2f}</span>',
            value or 0
        )

    def render_vendor_name(self, value):
        """Render vendor name."""
        return value or "â€”"

    def render_payment_method(self, value):
        """Render payment method or dash if empty."""
        return value or "â€”"

    def render_status(self, record):
        """Render expenditure status with appropriate styling."""
        status_classes = {
            'pending': 'status-pending',
            'approved': 'status-approved',
            'paid': 'status-completed',
            'rejected': 'status-rejected',
        }
        
        status_class = status_classes.get(record.status, 'status-inactive')
        return format_html(
            '<span class="status-badge {}">{}</span>',
            status_class,
            record.get_status_display()
        )

    def render_recorded_by(self, record):
        """Render recorded by user."""
        return record.recorded_by.get_full_name() if record.recorded_by else "â€”"

    def render_actions(self, record):
        """Render actions column based on status."""
        actions = []
        
        # View action (always available)
        actions.append(
            '<button class="btn-action btn-view" title="View Details" data-id="{}">'
            '<i class="fas fa-eye"></i></button>'.format(record.id)
        )
        
        # Edit action (for pending items)
        if record.status == 'pending':
            actions.append(
                '<button class="btn-action btn-edit" title="Edit Expenditure" data-id="{}">'
                '<i class="fas fa-edit"></i></button>'.format(record.id)
            )
            
            # Approve action (for pending items)
            actions.append(
                '<button class="btn-action btn-approve" title="Approve" data-id="{}">'
                '<i class="fas fa-check"></i></button>'.format(record.id)
            )
        
        return format_html(
            '<div class="action-buttons">{}</div>',
            ''.join(actions)
        )


class IncomeCategoryTable(tables.Table):
    """Table for displaying income categories."""

    name = tables.Column(verbose_name="Category Name")
    description = tables.Column(verbose_name="Description")
    is_active = tables.Column(empty_values=(), verbose_name="Status")
    income_count = tables.Column(empty_values=(), verbose_name="Income Records")
    total_amount = tables.Column(empty_values=(), verbose_name="Total Amount")
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Income
        template_name = "django_tables2/bootstrap4.html"
        fields = ("name", "description", "is_active", "income_count", "total_amount", "actions")
        attrs = {
            "class": "table table-hover category-table",
            "id": "income-category-table"
        }

    def render_description(self, value):
        """Render description or dash if empty."""
        return value or "â€”"

    def render_is_active(self, value):
        """Render active status."""
        if value:
            return format_html('<span class="status-badge status-active">Active</span>')
        else:
            return format_html('<span class="status-badge status-inactive">Inactive</span>')

    def render_income_count(self, record):
        """Render count of income records for this category."""
        count = Income.objects.filter(category=record).count()
        return format_html('<span class="count-badge">{}</span>', count)

    def render_total_amount(self, record):
        """Render total amount for this category."""
        from django.db.models import Sum
        total = Income.objects.filter(category=record).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return format_html(
            '<span class="amount-cell">Tsh {:,.2f}</span>',
            total
        )

    def render_actions(self, record):
        """Render actions column."""
        return format_html(
            '<div class="action-buttons">'
            '<button class="btn-action btn-edit" title="Edit Category" data-id="{}">'
            '<i class="fas fa-edit"></i></button>'
            '<button class="btn-action btn-toggle" title="Toggle Status" data-id="{}">'
            '<i class="fas fa-toggle-{}"></i></button>'
            '</div>',
            record.id,
            record.id,
            'on' if record.is_active else 'off'
        )


class ExpenditureCategoryTable(tables.Table):
    """Table for displaying expenditure categories."""

    name = tables.Column(verbose_name="Category Name")
    description = tables.Column(verbose_name="Description")
    is_active = tables.Column(empty_values=(), verbose_name="Status")
    expenditure_count = tables.Column(empty_values=(), verbose_name="Expenditure Records")
    total_amount = tables.Column(empty_values=(), verbose_name="Total Amount")
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Expenditure
        template_name = "django_tables2/bootstrap4.html"
        fields = ("name", "description", "is_active", "expenditure_count", "total_amount", "actions")
        attrs = {
            "class": "table table-hover category-table",
            "id": "expenditure-category-table"
        }

    def render_description(self, value):
        """Render description or dash if empty."""
        return value or "â€”"

    def render_is_active(self, value):
        """Render active status."""
        if value:
            return format_html('<span class="status-badge status-active">Active</span>')
        else:
            return format_html('<span class="status-badge status-inactive">Inactive</span>')

    def render_expenditure_count(self, record):
        """Render count of expenditure records for this category."""
        count = Expenditure.objects.filter(category=record).count()
        return format_html('<span class="count-badge">{}</span>', count)

    def render_total_amount(self, record):
        """Render total amount for this category."""
        from django.db.models import Sum
        total = Expenditure.objects.filter(category=record).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return format_html(
            '<span class="amount-cell">Tsh {:,.2f}</span>',
            total
        )

    def render_actions(self, record):
        """Render actions column."""
        return format_html(
            '<div class="action-buttons">'
            '<button class="btn-action btn-edit" title="Edit Category" data-id="{}">'
            '<i class="fas fa-edit"></i></button>'
            '<button class="btn-action btn-toggle" title="Toggle Status" data-id="{}">'
            '<i class="fas fa-toggle-{}"></i></button>'
            '</div>',
            record.id,
            record.id,
            'on' if record.is_active else 'off'
        )


