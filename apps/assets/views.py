"""
Views for asset and collateral management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Q, Count, Avg
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from datetime import datetime, timedelta
import json

from .models import (
    Asset, AssetCategory, AssetDocument, AssetValuation,
    Collateral, CollateralType, CollateralDocument, CollateralValuation
)
from apps.accounts.models import UserActivity
from apps.borrowers.models import Borrower
from apps.loans.models import Loan


@login_required
def dashboard(request):
    """Assets and collateral dashboard."""
    # Asset statistics
    asset_stats = {
        'total_assets': Asset.objects.count(),
        'active_assets': Asset.objects.filter(status='active').count(),
        'total_asset_value': Asset.objects.aggregate(
            total=Sum('current_value')
        )['total'] or 0,
        'assets_under_maintenance': Asset.objects.filter(
            status='under_maintenance'
        ).count(),
        'maintenance_due': Asset.objects.filter(
            next_maintenance_date__lte=timezone.now().date()
        ).count(),
    }
    
    # Collateral statistics
    collateral_stats = {
        'total_collaterals': Collateral.objects.count(),
        'pending_verification': Collateral.objects.filter(
            status='under_verification'
        ).count(),
        'held_collaterals': Collateral.objects.filter(
            status='held'
        ).count(),
        'total_collateral_value': Collateral.objects.aggregate(
            total=Sum('estimated_value')
        )['total'] or 0,
    }
    
    # Recent activities
    recent_assets = Asset.objects.select_related('category').order_by('-created_at')[:5]
    recent_collaterals = Collateral.objects.select_related(
        'borrower', 'collateral_type'
    ).order_by('-created_at')[:5]
    
    # Assets by category
    assets_by_category = AssetCategory.objects.annotate(
        asset_count=Count('assets'),
        total_value=Sum('assets__current_value')
    ).filter(asset_count__gt=0)
    
    # Collaterals by type
    collaterals_by_type = CollateralType.objects.annotate(
        collateral_count=Count('collaterals'),
        total_value=Sum('collaterals__estimated_value')
    ).filter(collateral_count__gt=0)
    
    context = {
        'asset_stats': asset_stats,
        'collateral_stats': collateral_stats,
        'recent_assets': recent_assets,
        'recent_collaterals': recent_collaterals,
        'assets_by_category': assets_by_category,
        'collaterals_by_type': collaterals_by_type,
        'title': 'Assets & Collateral Dashboard',
        'page_title': 'Assets & Collateral',
    }
    
    return render(request, 'assets/dashboard.html', context)


@login_required
def asset_list(request):
    """List all assets with filtering and search."""
    assets = Asset.objects.select_related('category', 'assigned_to').order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        assets = assets.filter(
            Q(asset_id__icontains=search_query) |
            Q(asset_name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id:
        assets = assets.filter(category_id=category_id)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # Filter by condition
    condition_filter = request.GET.get('condition', '')
    if condition_filter:
        assets = assets.filter(condition=condition_filter)
    
    # Pagination
    paginator = Paginator(assets, 25)
    page_number = request.GET.get('page')
    assets = paginator.get_page(page_number)
    
    # Get filter options
    categories = AssetCategory.objects.filter(is_active=True)
    
    context = {
        'assets': assets,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'status_filter': status_filter,
        'condition_filter': condition_filter,
        'asset_statuses': Asset.ASSET_STATUS_CHOICES,
        'asset_conditions': Asset.CONDITION_CHOICES,
        'title': 'Asset List',
        'page_title': 'Assets',
    }
    
    return render(request, 'assets/asset_list.html', context)


@login_required
def asset_detail(request, asset_id):
    """View asset details."""
    asset = get_object_or_404(Asset, id=asset_id)
    
    # Get asset documents
    documents = asset.documents.filter(is_active=True).order_by('-uploaded_date')
    
    # Get valuation history
    valuations = asset.valuations.order_by('-valuation_date')[:10]
    
    # Calculate depreciation schedule (next 5 years)
    depreciation_schedule = []
    if asset.status == 'active':
        annual_depreciation = (asset.purchase_value - asset.salvage_value) * (asset.depreciation_rate / 100)
        current_book_value = asset.book_value
        
        for year in range(1, 6):
            year_depreciation = min(annual_depreciation, current_book_value - asset.salvage_value)
            current_book_value -= year_depreciation
            
            depreciation_schedule.append({
                'year': timezone.now().year + year,
                'depreciation': year_depreciation,
                'book_value': max(current_book_value, asset.salvage_value)
            })
            
            if current_book_value <= asset.salvage_value:
                break
    
    context = {
        'asset': asset,
        'documents': documents,
        'valuations': valuations,
        'depreciation_schedule': depreciation_schedule,
        'title': f'Asset - {asset.asset_name}',
        'page_title': asset.asset_name,
    }
    
    return render(request, 'assets/asset_detail.html', context)


@login_required
def collateral_list(request):
    """List all collaterals with filtering and search."""
    collaterals = Collateral.objects.select_related(
        'borrower', 'collateral_type', 'loan'
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        collaterals = collaterals.filter(
            Q(collateral_id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(borrower__first_name__icontains=search_query) |
            Q(borrower__last_name__icontains=search_query) |
            Q(collateral_type__name__icontains=search_query)
        )
    
    # Filter by type
    type_id = request.GET.get('type', '')
    if type_id:
        collaterals = collaterals.filter(collateral_type_id=type_id)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        collaterals = collaterals.filter(status=status_filter)
    
    # Filter by borrower
    borrower_id = request.GET.get('borrower', '')
    if borrower_id:
        collaterals = collaterals.filter(borrower_id=borrower_id)
    
    # Pagination
    paginator = Paginator(collaterals, 25)
    page_number = request.GET.get('page')
    collaterals = paginator.get_page(page_number)
    
    # Get filter options
    collateral_types = CollateralType.objects.filter(is_active=True)
    borrowers = Borrower.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'collaterals': collaterals,
        'collateral_types': collateral_types,
        'borrowers': borrowers,
        'search_query': search_query,
        'type_id': type_id,
        'status_filter': status_filter,
        'borrower_id': borrower_id,
        'collateral_statuses': Collateral.COLLATERAL_STATUS_CHOICES,
        'title': 'Collateral List',
        'page_title': 'Collaterals',
    }
    
    return render(request, 'assets/collateral_list.html', context)


@login_required
def collateral_detail(request, collateral_id):
    """View collateral details."""
    collateral = get_object_or_404(Collateral, id=collateral_id)
    
    # Get collateral documents
    documents = collateral.documents.filter(is_active=True).order_by('-uploaded_date')
    
    # Get valuation history
    valuations = collateral.valuations.order_by('-valuation_date')[:10]
    
    # Get related loans
    related_loans = Loan.objects.filter(
        Q(collaterals=collateral) | Q(borrower=collateral.borrower)
    ).distinct().order_by('-created_at')[:5]
    
    context = {
        'collateral': collateral,
        'documents': documents,
        'valuations': valuations,
        'related_loans': related_loans,
        'title': f'Collateral - {collateral.title}',
        'page_title': collateral.title,
    }
    
    return render(request, 'assets/collateral_detail.html', context)


@login_required
def add_asset(request):
    """Add new asset."""
    if request.method == 'POST':
        # This will be implemented with forms
        pass

    categories = AssetCategory.objects.filter(is_active=True)
    users = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')

    context = {
        'categories': categories,
        'users': users,
        'title': 'Add Asset',
        'page_title': 'New Asset',
    }

    return render(request, 'assets/add_asset.html', context)


@login_required
def add_collateral(request):
    """Add new collateral."""
    if request.method == 'POST':
        # This will be implemented with forms
        pass

    collateral_types = CollateralType.objects.filter(is_active=True)
    borrowers = Borrower.objects.filter(is_active=True).order_by('first_name', 'last_name')
    loans = Loan.objects.filter(status__in=['approved', 'disbursed']).order_by('-created_at')

    context = {
        'collateral_types': collateral_types,
        'borrowers': borrowers,
        'loans': loans,
        'title': 'Add Collateral',
        'page_title': 'New Collateral',
    }

    return render(request, 'assets/add_collateral.html', context)


@login_required
def asset_reports(request):
    """Generate asset reports."""
    report_type = request.GET.get('report_type', 'summary')

    if report_type == 'summary':
        # Asset summary report
        total_assets = Asset.objects.count()
        total_value = Asset.objects.aggregate(total=Sum('current_value'))['total'] or 0

        # By category
        by_category = AssetCategory.objects.annotate(
            asset_count=Count('assets'),
            total_value=Sum('assets__current_value'),
            avg_value=Avg('assets__current_value')
        ).filter(asset_count__gt=0)

        # By status
        by_status = []
        for status_code, status_label in Asset.ASSET_STATUS_CHOICES:
            count = Asset.objects.filter(status=status_code).count()
            value = Asset.objects.filter(status=status_code).aggregate(
                total=Sum('current_value')
            )['total'] or 0

            if count > 0:
                by_status.append({
                    'status': status_label,
                    'count': count,
                    'value': value
                })

        # Depreciation summary
        total_purchase_value = Asset.objects.aggregate(
            total=Sum('purchase_value')
        )['total'] or 0
        total_accumulated_depreciation = sum(
            asset.accumulated_depreciation for asset in Asset.objects.all()
        )

        report_data = {
            'total_assets': total_assets,
            'total_value': total_value,
            'total_purchase_value': total_purchase_value,
            'total_accumulated_depreciation': total_accumulated_depreciation,
            'by_category': by_category,
            'by_status': by_status,
        }

    elif report_type == 'maintenance':
        # Maintenance report
        maintenance_due = Asset.objects.filter(
            next_maintenance_date__lte=timezone.now().date()
        ).select_related('category')

        under_maintenance = Asset.objects.filter(
            status='under_maintenance'
        ).select_related('category')

        warranty_expiring = Asset.objects.filter(
            warranty_expiry__lte=timezone.now().date() + timedelta(days=30),
            warranty_expiry__gte=timezone.now().date()
        ).select_related('category')

        report_data = {
            'maintenance_due': maintenance_due,
            'under_maintenance': under_maintenance,
            'warranty_expiring': warranty_expiring,
        }

    else:
        # Depreciation report
        assets_with_depreciation = []
        for asset in Asset.objects.filter(status='active').select_related('category'):
            assets_with_depreciation.append({
                'asset': asset,
                'accumulated_depreciation': asset.accumulated_depreciation,
                'book_value': asset.book_value,
                'depreciation_rate': asset.depreciation_rate,
            })

        report_data = {
            'assets_with_depreciation': assets_with_depreciation,
        }

    context = {
        'report_type': report_type,
        'report_data': report_data,
        'title': 'Asset Reports',
        'page_title': 'Asset Reports',
    }

    return render(request, 'assets/asset_reports.html', context)


@login_required
def collateral_reports(request):
    """Generate collateral reports."""
    report_type = request.GET.get('report_type', 'summary')

    if report_type == 'summary':
        # Collateral summary report
        total_collaterals = Collateral.objects.count()
        total_value = Collateral.objects.aggregate(
            total=Sum('estimated_value')
        )['total'] or 0

        # By type
        by_type = CollateralType.objects.annotate(
            collateral_count=Count('collaterals'),
            total_value=Sum('collaterals__estimated_value'),
            avg_value=Avg('collaterals__estimated_value')
        ).filter(collateral_count__gt=0)

        # By status
        by_status = []
        for status_code, status_label in Collateral.COLLATERAL_STATUS_CHOICES:
            count = Collateral.objects.filter(status=status_code).count()
            value = Collateral.objects.filter(status=status_code).aggregate(
                total=Sum('estimated_value')
            )['total'] or 0

            if count > 0:
                by_status.append({
                    'status': status_label,
                    'count': count,
                    'value': value
                })

        report_data = {
            'total_collaterals': total_collaterals,
            'total_value': total_value,
            'by_type': by_type,
            'by_status': by_status,
        }

    elif report_type == 'verification':
        # Verification status report
        pending_verification = Collateral.objects.filter(
            status='under_verification'
        ).select_related('borrower', 'collateral_type')

        verified_collaterals = Collateral.objects.filter(
            status='verified'
        ).select_related('borrower', 'collateral_type')

        rejected_collaterals = Collateral.objects.filter(
            status='rejected'
        ).select_related('borrower', 'collateral_type')

        report_data = {
            'pending_verification': pending_verification,
            'verified_collaterals': verified_collaterals,
            'rejected_collaterals': rejected_collaterals,
        }

    else:
        # Loan coverage report
        collaterals_with_loans = Collateral.objects.filter(
            loan__isnull=False
        ).select_related('loan', 'borrower', 'collateral_type')

        coverage_analysis = []
        for collateral in collaterals_with_loans:
            if collateral.loan:
                coverage_analysis.append({
                    'collateral': collateral,
                    'loan_amount': collateral.loan.amount_approved,
                    'ltv_ratio': collateral.loan_to_value_ratio,
                    'adequate_security': collateral.is_adequate_security,
                })

        report_data = {
            'coverage_analysis': coverage_analysis,
        }

    context = {
        'report_type': report_type,
        'report_data': report_data,
        'title': 'Collateral Reports',
        'page_title': 'Collateral Reports',
    }

    return render(request, 'assets/collateral_reports.html', context)
