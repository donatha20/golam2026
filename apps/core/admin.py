from django.contrib import admin
from .models import IncomeSource, ExpenseCategory


@admin.register(IncomeSource)
class IncomeSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'source_type', 'is_active')
    list_filter = ('is_active', 'source_type')
    search_fields = ('name', 'code')


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category_type', 'is_active')
    list_filter = ('is_active', 'category_type')
    search_fields = ('name', 'code')
