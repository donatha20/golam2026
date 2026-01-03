import django_tables2 as tables
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Loan, RepaymentSchedule


class DisbursedLoansTable(tables.Table):
    """Table for displaying disbursed loans with styled columns."""

    # Avatar column for visual consistency
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")

    # Borrower information
    borrower = tables.Column(empty_values=(), verbose_name="Borrower")

    # Loan details
    loan_number = tables.Column(verbose_name="Loan #")
    amount_approved = tables.Column(verbose_name="Amount")
    duration_months = tables.Column(verbose_name="Duration")
    disbursement_date = tables.DateColumn(format="M d, Y", verbose_name="Disbursed")
    loan_type = tables.Column(empty_values=(), verbose_name="Product")

    # Status and tracking
    status = tables.Column(empty_values=(), verbose_name="Status")
    outstanding_balance = tables.Column(verbose_name="Outstanding")
    disbursed_by = tables.Column(empty_values=(), verbose_name="Officer")

    # Actions
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Loan
        template_name = "django_tables2/bootstrap5.html"
        fields = ("avatar", "borrower", "loan_number", "amount_approved", "duration_months",
                 "disbursement_date", "loan_type", "status", "outstanding_balance", "disbursed_by", "actions")
        attrs = {
            "class": "table table-hover loan-table",
            "id": "disbursed-loans-table"
        }

    def render_avatar(self, record):
        """Render loan avatar with loan type initial."""
        initial = record.loan_type.name[:1].upper() if record.loan_type else "L"
        return format_html(
            '<div class="table-avatar">{}</div>',
            initial
        )

    def render_borrower(self, record):
        """Render borrower full name + ID."""
        borrower = record.borrower
        return format_html(
            '<div class="borrower-name-cell">'
            '<div class="borrower-full-name">{}</div>'
            '<div class="borrower-id">{}</div>'
            '</div>',
            borrower.get_full_name(),
            borrower.borrower_id
        )

    def render_loan_type(self, record):
        """Render loan type name."""
        return record.loan_type.name if record.loan_type else "—"

    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        return format_html(
            '<span class="amount-cell">₹{:,.2f}</span>',
            value or 0
        )

    def render_outstanding_balance(self, value):
        """Render outstanding balance with formatting."""
        if value and value > 0:
            return format_html(
                '<span class="amount-outstanding">₹{:,.2f}</span>',
                value
            )
        return format_html('<span class="amount-paid">₹0.00</span>')

    def render_duration_months(self, value):
        """Render duration with months label."""
        return f"{value} months" if value else "—"

    def render_status(self, record):
        """Render loan status with badge."""
        status_classes = {
            'pending': 'status-pending',
            'approved': 'status-approved',
            'disbursed': 'status-active',
            'active': 'status-active',
            'completed': 'status-completed',
            'defaulted': 'status-defaulted',
            'written_off': 'status-written-off',
        }

        status_class = status_classes.get(record.status, 'status-inactive')
        return format_html(
            '<span class="status-badge {}">{}</span>',
            status_class,
            record.get_status_display()
        )

    def render_disbursed_by(self, record):
        """Render disbursed by officer."""
        if record.disbursed_by:
            return record.disbursed_by.get_full_name()
        return "—"

    def render_actions(self, record):
        """Render actions column."""
        return format_html(
            '<div class="action-buttons">'
            '<button class="btn-action btn-view" title="View Details" data-id="{}">'
            '<i class="fas fa-eye"></i></button>'
            '<button class="btn-action btn-payment" title="Record Payment" data-id="{}">'
            '<i class="fas fa-credit-card"></i></button>'
            '<button class="btn-action btn-schedule" title="View Schedule" data-id="{}">'
            '<i class="fas fa-calendar-alt"></i></button>'
            '</div>',
            record.id,
            record.id,
            record.id
        )


class RepaidLoansTable(tables.Table):
    """Styled table for fully repaid loans."""

    # Avatar column for visual consistency
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")

    # Borrower information
    borrower = tables.Column(empty_values=(), verbose_name="Borrower")

    # Loan details
    loan_number = tables.Column(verbose_name="Loan #")
    loan_type = tables.Column(empty_values=(), verbose_name="Product")
    amount_approved = tables.Column(verbose_name="Amount")
    duration_months = tables.Column(verbose_name="Duration")

    # Dates
    disbursement_date = tables.DateColumn(verbose_name="Disbursed", format="M d, Y")
    completion_date = tables.DateColumn(verbose_name="Completed", format="M d, Y", empty_values=())

    # Officer and status
    created_by = tables.Column(empty_values=(), verbose_name="Officer")
    status = tables.Column(empty_values=(), orderable=False, verbose_name="Status")
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = Loan
        template_name = "django_tables2/bootstrap5.html"
        fields = ("avatar", "borrower", "loan_number", "loan_type", "amount_approved", "duration_months",
                "disbursement_date", "completion_date", "created_by", "status", "actions")
        attrs = {
            "class": "table table-hover loan-table",
            "id": "repaid-loans-table"
        }

    def render_avatar(self, record):
        """Render loan avatar with loan type initial."""
        initial = record.loan_type.name[:1].upper() if record.loan_type else "L"
        return format_html(
            '<div class="table-avatar">{}</div>',
            initial
        )

    def render_borrower(self, record):
        """Render borrower full name + ID."""
        borrower = record.borrower
        return format_html(
            '<div class="borrower-name-cell">'
            '<div class="borrower-full-name">{}</div>'
            '<div class="borrower-id">{}</div>'
            '</div>',
            borrower.get_full_name(),
            borrower.borrower_id
        )

    def render_loan_type(self, record):
        """Render loan type name."""
        return record.loan_type.name if record.loan_type else "—"

    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        return format_html(
            '<span class="amount-cell">₹{:,.2f}</span>',
            value or 0
        )

    def render_duration_months(self, value):
        """Render duration with months label."""
        return f"{value} months" if value else "—"

    def render_completion_date(self, record):
        """Render completion date or calculate from last payment."""
        # You might need to calculate this from the last repayment
        if hasattr(record, 'completion_date') and record.completion_date:
            return record.completion_date
        return "—"

    def render_created_by(self, record):
        """Render created by officer."""
        return record.created_by.get_full_name() if record.created_by else "—"

    def render_status(self, record):
        """Render completed status."""
        return format_html(
            '<span class="status-badge status-completed">Completed</span>'
        )

    def render_actions(self, record):
        """Render actions column."""
        return format_html(
            '<div class="action-buttons">'
            '<button class="btn-action btn-view" title="View Details" data-id="{}">'
            '<i class="fas fa-eye"></i></button>'
            '<button class="btn-action btn-history" title="Payment History" data-id="{}">'
            '<i class="fas fa-history"></i></button>'
            '</div>',
            record.id,
            record.id
        )


class ExpectedRepaymentsTable(tables.Table):
    """Table for upcoming or due scheduled repayments."""

    # Avatar column for visual consistency
    avatar = tables.Column(empty_values=(), orderable=False, verbose_name="")

    # Loan and borrower info
    loan_number = tables.Column(empty_values=(), verbose_name="Loan #")
    borrower = tables.Column(empty_values=(), verbose_name="Borrower")

    # Schedule details
    installment_number = tables.Column(verbose_name="Installment")
    due_date = tables.DateColumn(verbose_name="Due Date", format="M d, Y")
    amount_due = tables.Column(verbose_name="Amount Due")

    # Status and tracking
    status = tables.Column(empty_values=(), verbose_name="Status")
    days_overdue = tables.Column(empty_values=(), verbose_name="Days Overdue")
    loan_balance = tables.Column(empty_values=(), verbose_name="Loan Balance")

    # Group info (if applicable)
    group_info = tables.Column(empty_values=(), verbose_name="Group")

    # Actions
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = RepaymentSchedule
        template_name = "django_tables2/bootstrap5.html"
        fields = ("avatar", "loan_number", "borrower", "installment_number", "due_date", "amount_due",
                "status", "days_overdue", "loan_balance", "group_info", "actions")
        attrs = {
            "class": "table table-hover repayment-table",
            "id": "expected-repayments-table"
        }

    def render_avatar(self, record):
        """Render repayment avatar with status indicator."""
        if record.status == 'paid':
            icon = "✓"
            color = "#16a34a"
        elif record.status == 'missed':
            icon = "!"
            color = "#dc2626"
        else:
            icon = "₹"
            color = "#2b7a76"

        return format_html(
            '<div class="table-avatar" style="background-color: {}20; color: {}">{}</div>',
            color, color, icon
        )

    def render_loan_number(self, record):
        """Render loan number."""
        return record.loan.loan_number

    def render_borrower(self, record):
        """Render borrower information."""
        borrower = record.loan.borrower
        return format_html(
            '<div class="borrower-name-cell">'
            '<div class="borrower-full-name">{}</div>'
            '<div class="borrower-id">{}</div>'
            '</div>',
            borrower.get_full_name(),
            borrower.borrower_id
        )

    def render_amount_due(self, value):
        """Render amount due with currency formatting."""
        return format_html(
            '<span class="amount-cell">₹{:,.2f}</span>',
            value or 0
        )

    def render_status(self, record):
        """Render repayment status with appropriate styling."""
        status_classes = {
            'pending': 'status-pending',
            'paid': 'status-completed',
            'missed': 'status-overdue',
            'defaulted': 'status-defaulted',
        }

        status_class = status_classes.get(record.status, 'status-inactive')
        return format_html(
            '<span class="status-badge {}">{}</span>',
            status_class,
            record.get_status_display()
        )

    def render_days_overdue(self, record):
        """Calculate and render days overdue."""
        from django.utils import timezone

        if record.status in ['paid', 'completed']:
            return format_html('<span class="days-current">Paid</span>')

        today = timezone.now().date()
        if record.due_date < today:
            days_overdue = (today - record.due_date).days
            if days_overdue <= 30:
                css_class = "days-1-30"
            elif days_overdue <= 90:
                css_class = "days-31-90"
            else:
                css_class = "days-90-plus"

            return format_html(
                '<span class="{}">{} days</span>',
                css_class, days_overdue
            )
        else:
            return format_html('<span class="days-current">Current</span>')

    def render_loan_balance(self, record):
        """Render loan outstanding balance."""
        balance = record.loan.outstanding_balance or 0
        if balance > 0:
            return format_html(
                '<span class="amount-outstanding">₹{:,.2f}</span>',
                balance
            )
        return format_html('<span class="amount-paid">₹0.00</span>')

    def render_group_info(self, record):
        """Render group information if applicable."""
        if hasattr(record.loan, 'group_loan') and record.loan.group_loan:
            return record.loan.group_loan.group.name
        return "—"

    def render_actions(self, record):
        """Render actions column."""
        if record.status == 'pending':
            return format_html(
                '<div class="action-buttons">'
                '<button class="btn-action btn-payment" title="Record Payment" data-id="{}">'
                '<i class="fas fa-credit-card"></i></button>'
                '<button class="btn-action btn-view" title="View Details" data-id="{}">'
                '<i class="fas fa-eye"></i></button>'
                '</div>',
                record.id,
                record.id
            )
        else:
            return format_html(
                '<div class="action-buttons">'
                '<button class="btn-action btn-view" title="View Details" data-id="{}">'
                '<i class="fas fa-eye"></i></button>'
                '</div>',
                record.id
            )
