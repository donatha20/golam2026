# loans/filters.py

import django_filters
from django import forms
from django.db.models import Q
from datetime import date, timedelta
from apps.loans.models import Loan, RepaymentSchedule, LoanType
from apps.borrowers.models import Borrower
from apps.core.models import LoanStatusChoices

CATEGORY_CHOICES = [('', 'All'), ('individual', 'Individual'), ('group', 'Group')]
GENDER_CHOICES = [('', 'All'), ('male', 'Male'), ('female', 'Female')]
STATUS_CHOICES = [('', 'All')] + list(LoanStatusChoices.choices)

# Days overdue choices for outstanding loans
DAYS_OVERDUE_CHOICES = [
    ('', 'All Loans'),
    ('current', 'Current (0 days)'),
    ('1-30', '1-30 days overdue'),
    ('31-90', '31-90 days overdue'),
    ('90+', '90+ days overdue'),
]

class LoanBaseFilter(django_filters.FilterSet):
    """Base filter for loan-related views."""
    branch = django_filters.CharFilter(
        field_name='borrower__branch__name',
        lookup_expr='icontains',
        label='Branch'
    )
    officer = django_filters.CharFilter(
        field_name='borrower__registered_by__first_name',
        lookup_expr='icontains',
        label='Officer'
    )
    category = django_filters.ChoiceFilter(
        field_name='borrower__category',
        choices=CATEGORY_CHOICES,
        label='Category'
    )
    gender = django_filters.ChoiceFilter(
        field_name='borrower__gender',
        choices=GENDER_CHOICES,
        label='Gender'
    )
    sector = django_filters.CharFilter(
        field_name='borrower__occupation',
        lookup_expr='icontains',
        label='Sector'
    )
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=STATUS_CHOICES,
        label='Status'
    )
    amount_min = django_filters.NumberFilter(
        field_name='amount_approved',
        lookup_expr='gte',
        label='Min Amount'
    )
    amount_max = django_filters.NumberFilter(
        field_name='amount_approved',
        lookup_expr='lte',
        label='Max Amount'
    )

    class Meta:
        model = Loan
        fields = ['branch', 'officer', 'category', 'gender', 'sector', 'status', 'amount_min', 'amount_max']


class LoanFilter(LoanBaseFilter):
    """Filter for general loan views."""
    borrower_name = django_filters.CharFilter(
        method='filter_borrower_name',
        label='Borrower Name'
    )
    
    def filter_borrower_name(self, queryset, name, value):
        return queryset.filter(
            Q(borrower__first_name__icontains=value) |
            Q(borrower__last_name__icontains=value)
        )

    class Meta(LoanBaseFilter.Meta):
        fields = LoanBaseFilter.Meta.fields + ['borrower_name']


class RepaymentScheduleFilter(django_filters.FilterSet):
    """Filter for repayment schedule views."""
    loan_number = django_filters.CharFilter(
        field_name='loan__loan_number',
        lookup_expr='icontains',
        label='Loan Number'
    )
    borrower_name = django_filters.CharFilter(
        method='filter_borrower_name',
        label='Borrower Name'
    )
    due_date_from = django_filters.DateFilter(
        field_name='due_date',
        lookup_expr='gte',
        label='Due Date From'
    )
    due_date_to = django_filters.DateFilter(
        field_name='due_date',
        lookup_expr='lte',
        label='Due Date To'
    )
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=[
            ('', 'All'),
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('missed', 'Missed'),
            ('rolled_over', 'Rolled Over'),
            ('defaulted', 'Defaulted')
        ],
        label='Status'
    )
    
    def filter_borrower_name(self, queryset, name, value):
        return queryset.filter(
            Q(loan__borrower__first_name__icontains=value) |
            Q(loan__borrower__last_name__icontains=value)
        )

    class Meta:
        model = RepaymentSchedule
        fields = ['loan_number', 'borrower_name', 'due_date_from', 'due_date_to', 'status']


class OutstandingLoansFilter(django_filters.FilterSet):
    """Filter for outstanding loans view."""
    borrower = django_filters.CharFilter(
        method='filter_borrower_name',
        label='Borrower Name',
        widget=forms.TextInput(attrs={
            'class': 'borrower-search-filter',
            'placeholder': 'Type borrower name to search...',
            'autocomplete': 'off'
        })
    )
    loan_product = django_filters.ModelChoiceFilter(
        field_name='loan_type',
        queryset=None,  # Will be set in __init__
        empty_label='All Loan Products',
        widget=forms.Select(attrs={
            'class': 'form-select filter-select'
        })
    )
    loan_officer = django_filters.CharFilter(
        field_name='loan_officer',
        lookup_expr='icontains',
        label='Loan Officer',
        widget=forms.TextInput(attrs={
            'class': 'form-input filter-input',
            'placeholder': 'Enter officer name...'
        })
    )
    days_overdue = django_filters.ChoiceFilter(
        method='filter_days_overdue',
        choices=DAYS_OVERDUE_CHOICES,
        label='Days Overdue',
        widget=forms.Select(attrs={
            'class': 'form-select filter-select'
        })
    )
    outstanding_min = django_filters.NumberFilter(
        field_name='outstanding_balance',
        lookup_expr='gte',
        label='Min Outstanding',
        widget=forms.NumberInput(attrs={
            'class': 'form-input filter-input',
            'placeholder': '0',
            'min': '0',
            'step': '1000'
        })
    )
    outstanding_max = django_filters.NumberFilter(
        field_name='outstanding_balance',
        lookup_expr='lte',
        label='Max Outstanding',
        widget=forms.NumberInput(attrs={
            'class': 'form-input filter-input',
            'placeholder': 'No limit',
            'min': '0',
            'step': '1000'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for choice fields
        from apps.accounts.models import CustomUser
        
        self.filters['loan_product'].queryset = LoanType.objects.all()
    
    def filter_borrower_name(self, queryset, name, value):
        """Filter by borrower first name or last name."""
        return queryset.filter(
            Q(borrower__first_name__icontains=value) |
            Q(borrower__last_name__icontains=value)
        )
    
    def filter_days_overdue(self, queryset, name, value):
        """Filter loans based on days overdue."""
        if not value:
            return queryset
            
        today = date.today()
        
        if value == 'current':
            # Current loans (no overdue payments)
            return queryset.filter(
                repayment_schedules__due_date__gte=today,
                repayment_schedules__status='pending'
            ).distinct()
        elif value == '1-30':
            # 1-30 days overdue
            start_date = today - timedelta(days=30)
            end_date = today - timedelta(days=1)
            return queryset.filter(
                repayment_schedules__due_date__range=[start_date, end_date],
                repayment_schedules__status='pending'
            ).distinct()
        elif value == '31-90':
            # 31-90 days overdue
            start_date = today - timedelta(days=90)
            end_date = today - timedelta(days=31)
            return queryset.filter(
                repayment_schedules__due_date__range=[start_date, end_date],
                repayment_schedules__status='pending'
            ).distinct()
        elif value == '90+':
            # 90+ days overdue
            overdue_date = today - timedelta(days=90)
            return queryset.filter(
                repayment_schedules__due_date__lt=overdue_date,
                repayment_schedules__status='pending'
            ).distinct()
        
        return queryset

    class Meta:
        model = Loan
        fields = ['borrower', 'loan_product', 'loan_officer', 'days_overdue', 'outstanding_min', 'outstanding_max']
