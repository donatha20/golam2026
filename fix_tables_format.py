#!/usr/bin/env python
"""Fix all format_html with {:,.2f} by pre-formatting the amounts."""

with open('apps/loans/tables.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all the problem patterns
replacements = [
    # Pattern 1: render_amount_approved in DisbursedLoansTable
    (
        '''    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        return format_html(
            '<span class="amount-cell">Tsh {:,.2f}</span>',
            value or 0
        )''',
        '''    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        try:
            amount = float(value) if value else 0
            formatted = "{:,.2f}".format(amount)
        except (ValueError, TypeError):
            formatted = "0.00"
        return format_html(
            '<span class="amount-cell">Tsh {}</span>',
            formatted
        )'''
    ),
    # Pattern 2: render_outstanding_balance in DisbursedLoansTable
    (
        '''    def render_outstanding_balance(self, value):
        """Render outstanding balance with formatting."""
        if value and value > 0:
            return format_html(
                '<span class="amount-outstanding">Tsh {:,.2f}</span>',
                value
            )
        return format_html('<span class="amount-paid">Tsh 0.00</span>')''',
        '''    def render_outstanding_balance(self, value):
        """Render outstanding balance with formatting."""
        try:
            amount = float(value) if value else 0
        except (ValueError, TypeError):
            amount = 0
        if amount > 0:
            formatted = "{:,.2f}".format(amount)
            return format_html(
                '<span class="amount-outstanding">Tsh {}</span>',
                formatted
            )
        return format_html('<span class="amount-paid">Tsh 0.00</span>')'''
    ),
    # Pattern 3: render_amount_approved in RepaidLoansTable  
    (
        '''    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        try:
            amount = float(value) if value else 0
        except (ValueError, TypeError):
            amount = 0
        return format_html(
            '<span class="amount-cell">Tsh {:,.2f}</span>',
            amount
        )

    def render_duration_months(self, value):
        """Render duration with months label."""
        return f"{value} months" if value else "–"

    def render_completion_date(self, record):''',
        '''    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        try:
            amount = float(value) if value else 0
            formatted = "{:,.2f}".format(amount)
        except (ValueError, TypeError):
            formatted = "0.00"
        return format_html(
            '<span class="amount-cell">Tsh {}</span>',
            formatted
        )

    def render_duration_months(self, value):
        """Render duration with months label."""
        return f"{value} months" if value else "–"

    def render_completion_date(self, record):'''
    ),
    # Pattern 4: render_loan_balance in ExpectedRepaymentsTable
    (
        '''    def render_loan_balance(self, record):
        """Render loan outstanding balance."""
        balance = record.loan.outstanding_balance or 0
        if balance > 0:
            return format_html(
                '<span class="amount-outstanding">Tsh {:,.2f}</span>',
                balance
            )
        return format_html('<span class="amount-paid">Tsh 0.00</span>')''',
        '''    def render_loan_balance(self, record):
        """Render loan outstanding balance."""
        try:
            balance = float(record.loan.outstanding_balance or 0)
        except (ValueError, TypeError):
            balance = 0
        if balance > 0:
            formatted = "{:,.2f}".format(balance)
            return format_html(
                '<span class="amount-outstanding">Tsh {}</span>',
                formatted
            )
        return format_html('<span class="amount-paid">Tsh 0.00</span>')'''
    ),
    # Pattern 5: render_amount_approved in NonPerformingLoansTable
    (
        '''    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        try:
            amount = float(value) if value else 0
        except (ValueError, TypeError):
            amount = 0
        return format_html(
            '<span class="amount-cell">Tsh {:,.2f}</span>',
            amount
        )

    def render_outstanding_balance(self, value):
        """Render outstanding balance with NPL styling."""
        try:
            amount = float(value) if value else 0
        except (ValueError, TypeError):
            amount = 0
        if amount > 0:
            return format_html(
                '<span class="amount-outstanding npl-amount">Tsh {:,.2f}</span>',
                amount
            )
        return format_html('<span class="amount-paid">Tsh 0.00</span>')

    def render_days_overdue(self, record):''',
        '''    def render_amount_approved(self, value):
        """Render amount with currency formatting."""
        try:
            amount = float(value) if value else 0
            formatted = "{:,.2f}".format(amount)
        except (ValueError, TypeError):
            formatted = "0.00"
        return format_html(
            '<span class="amount-cell">Tsh {}</span>',
            formatted
        )

    def render_outstanding_balance(self, value):
        """Render outstanding balance with NPL styling."""
        try:
            amount = float(value) if value else 0
            formatted = "{:,.2f}".format(amount)
        except (ValueError, TypeError):
            formatted = "0.00"
        if amount > 0:
            return format_html(
                '<span class="amount-outstanding npl-amount">Tsh {}</span>',
                formatted
            )
        return format_html('<span class="amount-paid">Tsh 0.00</span>')

    def render_days_overdue(self, record):'''
    ),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"✓ Applied fix for: {old[:50]}...")
    else:
        print(f"⚠ Could not find pattern: {old[:50]}...")

with open('apps/loans/tables.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ All fixes applied!")
