"""
Django filters for finance tracker.
"""
import django_filters
from django import forms
from django.db.models import Q
from .models import Income, Expenditure, IncomeCategory, ExpenditureCategory


class IncomeFilter(django_filters.FilterSet):
    """Filter for income records."""
    
    # Search filter
    search = django_filters.CharFilter(
        method='filter_search',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by income ID, description, or source...'
        }),
        label='Search'
    )
    
    # Category filter
    category = django_filters.ModelChoiceFilter(
        queryset=IncomeCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Categories',
        label='Category'
    )
    
    # Source filter
    source = django_filters.ChoiceFilter(
        choices=Income.INCOME_SOURCES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Sources',
        label='Source'
    )
    
    # Date range filters
    income_date_from = django_filters.DateFilter(
        field_name='income_date',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='From Date'
    )
    
    income_date_to = django_filters.DateFilter(
        field_name='income_date',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='To Date'
    )
    
    # Amount range filters
    amount_min = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min amount',
            'step': '0.01'
        }),
        label='Min Amount'
    )
    
    amount_max = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max amount',
            'step': '0.01'
        }),
        label='Max Amount'
    )
    
    # Payment method filter
    payment_method = django_filters.ChoiceFilter(
        choices=Income.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Payment Methods',
        label='Payment Method'
    )
    
    # Status filter
    status = django_filters.ChoiceFilter(
        choices=Income.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Statuses',
        label='Status'
    )
    
    class Meta:
        model = Income
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Custom search filter."""
        if value:
            return queryset.filter(
                Q(income_id__icontains=value) |
                Q(description__icontains=value) |
                Q(received_from__icontains=value) |
                Q(reference_number__icontains=value)
            )
        return queryset


class ExpenditureFilter(django_filters.FilterSet):
    """Filter for expenditure records."""
    
    # Search filter
    search = django_filters.CharFilter(
        method='filter_search',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by expenditure ID, description, or vendor...'
        }),
        label='Search'
    )
    
    # Category filter
    category = django_filters.ModelChoiceFilter(
        queryset=ExpenditureCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Categories',
        label='Category'
    )
    
    # Type filter
    expenditure_type = django_filters.ChoiceFilter(
        choices=Expenditure.EXPENDITURE_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Types',
        label='Type'
    )
    
    # Date range filters
    expenditure_date_from = django_filters.DateFilter(
        field_name='expenditure_date',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='From Date'
    )
    
    expenditure_date_to = django_filters.DateFilter(
        field_name='expenditure_date',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='To Date'
    )
    
    # Amount range filters
    amount_min = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min amount',
            'step': '0.01'
        }),
        label='Min Amount'
    )
    
    amount_max = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max amount',
            'step': '0.01'
        }),
        label='Max Amount'
    )
    
    # Payment method filter
    payment_method = django_filters.ChoiceFilter(
        choices=Expenditure.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Payment Methods',
        label='Payment Method'
    )
    
    # Status filter
    status = django_filters.ChoiceFilter(
        choices=Expenditure.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Statuses',
        label='Status'
    )
    
    # Vendor filter
    vendor_name = django_filters.CharFilter(
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search vendor name...'
        }),
        label='Vendor'
    )
    
    class Meta:
        model = Expenditure
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Custom search filter."""
        if value:
            return queryset.filter(
                Q(expenditure_id__icontains=value) |
                Q(description__icontains=value) |
                Q(vendor_name__icontains=value) |
                Q(reference_number__icontains=value)
            )
        return queryset


class BudgetFilter(django_filters.FilterSet):
    """Filter for budget records."""
    
    # Search filter
    search = django_filters.CharFilter(
        method='filter_search',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by budget ID or name...'
        }),
        label='Search'
    )
    
    # Budget period filter
    budget_period = django_filters.ChoiceFilter(
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('semi_annual', 'Semi-Annual'),
            ('annual', 'Annual'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Periods',
        label='Budget Period'
    )
    
    # Status filter
    status = django_filters.ChoiceFilter(
        choices=[
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('active', 'Active'),
            ('closed', 'Closed'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        empty_label='All Statuses',
        label='Status'
    )
    
    # Date range filters
    period_start_from = django_filters.DateFilter(
        field_name='period_start',
        lookup_expr='gte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Period Start From'
    )
    
    period_end_to = django_filters.DateFilter(
        field_name='period_end',
        lookup_expr='lte',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Period End To'
    )
    
    class Meta:
        model = None  # Will be set dynamically
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Custom search filter."""
        if value:
            return queryset.filter(
                Q(budget_id__icontains=value) |
                Q(name__icontains=value) |
                Q(description__icontains=value)
            )
        return queryset


class CategoryFilter(django_filters.FilterSet):
    """Filter for category records."""
    
    # Search filter
    search = django_filters.CharFilter(
        method='filter_search',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by category name or description...'
        }),
        label='Search'
    )
    
    # Status filter
    is_active = django_filters.BooleanFilter(
        widget=forms.Select(
            choices=[
                ('', 'All Categories'),
                (True, 'Active Only'),
                (False, 'Inactive Only')
            ],
            attrs={'class': 'form-select'}
        ),
        label='Status'
    )
    
    class Meta:
        model = None  # Will be set dynamically
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Custom search filter."""
        if value:
            return queryset.filter(
                Q(name__icontains=value) |
                Q(description__icontains=value)
            )
        return queryset


