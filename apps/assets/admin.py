"""
Admin configuration for assets and collateral management.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AssetCategory, Asset, AssetDocument, AssetValuation,
    CollateralType, Collateral, CollateralDocument, CollateralValuation
)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'depreciation_rate', 'useful_life_years', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


class AssetDocumentInline(admin.TabularInline):
    model = AssetDocument
    extra = 0
    readonly_fields = ['file_size', 'uploaded_date', 'uploaded_by']


class AssetValuationInline(admin.TabularInline):
    model = AssetValuation
    extra = 0
    readonly_fields = ['created_at', 'created_by']


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        'asset_id', 'asset_name', 'category', 'purchase_value', 'current_value', 
        'status', 'condition', 'assigned_to', 'created_at'
    ]
    list_filter = ['status', 'condition', 'category', 'created_at']
    search_fields = ['asset_id', 'asset_name', 'serial_number', 'model_number']
    readonly_fields = ['asset_id', 'age_in_years', 'accumulated_depreciation', 'book_value']
    inlines = [AssetDocumentInline, AssetValuationInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('asset_id', 'asset_name', 'category', 'description')
        }),
        ('Financial Information', {
            'fields': (
                'purchase_date', 'purchase_value', 'current_value', 'salvage_value',
                'depreciation_method', 'custom_depreciation_rate'
            )
        }),
        ('Physical Information', {
            'fields': (
                'serial_number', 'model_number', 'manufacturer', 'condition'
            )
        }),
        ('Location and Assignment', {
            'fields': ('location', 'department', 'assigned_to')
        }),
        ('Status and Maintenance', {
            'fields': (
                'status', 'warranty_expiry', 'last_maintenance_date', 'next_maintenance_date'
            )
        }),
        ('Additional Information', {
            'fields': (
                'supplier', 'purchase_order_number', 'insurance_policy_number', 
                'insurance_expiry', 'notes'
            )
        }),
        ('Calculated Values', {
            'fields': ('age_in_years', 'accumulated_depreciation', 'book_value'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AssetDocument)
class AssetDocumentAdmin(admin.ModelAdmin):
    list_display = ['asset', 'document_type', 'title', 'file_size_display', 'uploaded_date', 'uploaded_by']
    list_filter = ['document_type', 'uploaded_date', 'is_active']
    search_fields = ['asset__asset_id', 'asset__asset_name', 'title']
    readonly_fields = ['file_size', 'uploaded_date', 'uploaded_by']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = "File Size"


@admin.register(CollateralType)
class CollateralTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'minimum_value', 'loan_to_value_ratio', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


class CollateralDocumentInline(admin.TabularInline):
    model = CollateralDocument
    extra = 0
    readonly_fields = ['file_size', 'uploaded_date', 'uploaded_by', 'verified_date', 'verified_by']


class CollateralValuationInline(admin.TabularInline):
    model = CollateralValuation
    extra = 0
    readonly_fields = ['created_at', 'created_by']


@admin.register(Collateral)
class CollateralAdmin(admin.ModelAdmin):
    list_display = [
        'collateral_id', 'title', 'borrower', 'collateral_type', 'estimated_value',
        'status', 'condition', 'created_at'
    ]
    list_filter = ['status', 'condition', 'collateral_type', 'ownership_status', 'created_at']
    search_fields = [
        'collateral_id', 'title', 'borrower__first_name', 'borrower__last_name',
        'serial_number', 'registration_number'
    ]
    readonly_fields = ['collateral_id', 'loan_to_value_ratio', 'is_adequate_security', 'insurance_status']
    inlines = [CollateralDocumentInline, CollateralValuationInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('collateral_id', 'borrower', 'loan', 'collateral_type', 'title', 'description')
        }),
        ('Physical Details', {
            'fields': (
                'brand_model', 'serial_number', 'year_of_manufacture', 'condition'
            )
        }),
        ('Valuation Information', {
            'fields': (
                'estimated_value', 'market_value', 'forced_sale_value', 
                'valuation_date', 'valuation_method', 'valuated_by'
            )
        }),
        ('Location and Ownership', {
            'fields': (
                'location', 'ownership_status', 'owner_name', 'owner_relationship'
            )
        }),
        ('Legal Information', {
            'fields': (
                'registration_number', 'registration_authority', 'legal_title_holder',
                'encumbrance_details'
            )
        }),
        ('Insurance Information', {
            'fields': (
                'is_insured', 'insurance_company', 'insurance_policy_number',
                'insurance_value', 'insurance_expiry'
            )
        }),
        ('Status and Verification', {
            'fields': (
                'status', 'verification_date', 'verified_by', 'verification_notes'
            )
        }),
        ('Additional Information', {
            'fields': ('special_conditions', 'notes')
        }),
        ('Calculated Values', {
            'fields': ('loan_to_value_ratio', 'is_adequate_security', 'insurance_status'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CollateralDocument)
class CollateralDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'collateral', 'document_type', 'title', 'file_size_display', 
        'is_verified', 'uploaded_date', 'uploaded_by'
    ]
    list_filter = ['document_type', 'is_verified', 'uploaded_date', 'is_active']
    search_fields = ['collateral__collateral_id', 'collateral__title', 'title']
    readonly_fields = ['file_size', 'uploaded_date', 'uploaded_by']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = "File Size"


