
import django_tables2 as tables
from django.utils.html import format_html
from django.urls import reverse
from .models import Income, Expenditure


class IncomeApprovalTable(tables.Table):
    """Table for displaying income records pending approval."""

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
    recorded_by = tables.Column(empty_values=(), verbose_name="Recorded By")
    created_at = tables.DateTimeColumn(format="M d, Y H:i", verbose_name="Created")
    
    # Approval Actions
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Income
        template_name = "django_tables2/bootstrap4.html"
        fields = ("avatar", "income_id", "source", "category", "amount", "income_date", 
                 "received_from", "recorded_by", "created_at", "actions")
        attrs = {
            "class": "table table-hover income-approval-table",
            "id": "income-approval-table"
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
        return record.category.name if record.category else "—"

    def render_amount(self, value):
        """Render amount with currency formatting."""
        try:
            amount_display = f"{float(value or 0):,.2f}"
        except (TypeError, ValueError):
            amount_display = str(value or 0)

        return format_html(
            '<span class="amount-cell income-amount">Tsh {}</span>',
            amount_display
        )

    def render_received_from(self, value):
        """Render received from or dash if empty."""
        return value or "—"

    def render_recorded_by(self, record):
        """Render recorded by user."""
        return record.recorded_by.get_full_name() if record.recorded_by else "—"

    def render_actions(self, record):
        """Render approval actions."""
        approve_url = reverse('finance_tracker:approve_income', args=[record.id])
        reject_url = reverse('finance_tracker:reject_income', args=[record.id])
        
        return format_html(
            '<div class="action-buttons approval-actions">'
            '<a href="{}" class="btn btn-success btn-sm" title="Approve">'
            '<i class="fas fa-check"></i></a>'
            '<a href="{}" class="btn btn-danger btn-sm" title="Reject">'
            '<i class="fas fa-times"></i></a>'
            '</div>',
            approve_url,
            reject_url
        )


class ExpenditureApprovalTable(tables.Table):
    """Table for displaying expenditure records pending approval."""

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
    recorded_by = tables.Column(empty_values=(), verbose_name="Recorded By")
    created_at = tables.DateTimeColumn(format="M d, Y H:i", verbose_name="Created")
    
    # Approval Actions
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Expenditure
        template_name = "django_tables2/bootstrap4.html"
        fields = ("avatar", "expenditure_id", "expenditure_type", "category", "amount", 
                 "expenditure_date", "vendor_name", "recorded_by", "created_at", "actions")
        attrs = {
            "class": "table table-hover expenditure-approval-table",
            "id": "expenditure-approval-table"
        }

    def render_avatar(self, record):
        """Render expenditure avatar with type initial."""
        initial = record.get_expenditure_type_display()[:1].upper()
        return format_html(
            '<div class="table-avatar expenditure-avatar">{}</div>',
            initial
        )

    def render_expenditure_type(self, record):
        """Render expenditure type display name."""
        return record.get_expenditure_type_display()

    def render_category(self, record):
        """Render category name or dash if none."""
        return record.category.name if record.category else "—"

    def render_amount(self, value):
        """Render amount with currency formatting."""
        try:
            amount_display = f"{float(value or 0):,.2f}"
        except (TypeError, ValueError):
            amount_display = str(value or 0)

        return format_html(
            '<span class="amount-cell expenditure-amount">Tsh {}</span>',
            amount_display
        )

    def render_vendor_name(self, value):
        """Render vendor name or dash if empty."""
        return value or "—"

    def render_recorded_by(self, record):
        """Render recorded by user."""
        return record.recorded_by.get_full_name() if record.recorded_by else "—"

    def render_actions(self, record):
        """Render approval actions."""
        approve_url = reverse('finance_tracker:approve_expenditure', args=[record.id])
        reject_url = reverse('finance_tracker:reject_expenditure', args=[record.id])
        
        return format_html(
            '<div class="action-buttons approval-actions">'
            '<a href="{}" class="btn btn-success btn-sm" title="Approve">'
            '<i class="fas fa-check"></i></a>'
            '<a href="{}" class="btn btn-danger btn-sm" title="Reject">'
            '<i class="fas fa-times"></i></a>'
            '</div>',
            approve_url,
            reject_url
        )


