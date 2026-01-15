"""
Advanced analytics utilities for business intelligence.
"""
# pandas and numpy not needed - using Django ORM and Python built-ins
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class LoanAnalytics:
    """Advanced loan portfolio analytics."""
    
    @staticmethod
    def calculate_portfolio_metrics(loans_queryset):
        """Calculate comprehensive portfolio metrics."""
        from apps.loans.models import Loan
        from apps.core.models import LoanStatusChoices
        
        total_loans = loans_queryset.count()
        if total_loans == 0:
            return {}
        
        # Basic metrics
        metrics = loans_queryset.aggregate(
            total_disbursed=Sum(Coalesce('amount_approved', 'amount_requested')),
            total_outstanding=Sum('outstanding_balance'),
            avg_loan_size=Avg(Coalesce('amount_approved', 'amount_requested')),
            total_interest_earned=Sum('total_interest'),
        )
        
        # Status breakdown
        status_breakdown = {}
        status_mappings = [
            (LoanStatusChoices.ACTIVE, 'active'),
            (LoanStatusChoices.COMPLETED, 'completed'),
            (LoanStatusChoices.DEFAULTED, 'defaulted'),
            (LoanStatusChoices.WRITTEN_OFF, 'written_off'),
        ]
        for status_value, label in status_mappings:
            count = loans_queryset.filter(status=status_value).count()
            amount = loans_queryset.filter(status=status_value).aggregate(
                total=Sum(Coalesce('amount_approved', 'amount_requested'))
            )['total'] or Decimal('0.00')
            
            status_breakdown[label] = {
                'count': count,
                'amount': amount,
                'percentage': (count / total_loans) * 100 if total_loans > 0 else 0
            }
        
        # Risk metrics
        overdue_loans = loans_queryset.filter(
            id__in=Loan.objects.overdue().values('id')
        )
        portfolio_at_risk = overdue_loans.aggregate(
            amount=Sum('outstanding_balance')
        )['amount'] or Decimal('0.00')
        
        total_outstanding = metrics['total_outstanding'] or Decimal('0.00')
        par_ratio = (portfolio_at_risk / total_outstanding * 100) if total_outstanding > 0 else 0
        
        # Performance metrics
        completed_loans = loans_queryset.filter(status=LoanStatusChoices.COMPLETED)
        default_rate = (status_breakdown['defaulted']['count'] / total_loans * 100) if total_loans > 0 else 0
        completion_rate = (completed_loans.count() / total_loans * 100) if total_loans > 0 else 0
        
        return {
            'basic_metrics': metrics,
            'status_breakdown': status_breakdown,
            'risk_metrics': {
                'portfolio_at_risk': portfolio_at_risk,
                'par_ratio': par_ratio,
                'default_rate': default_rate,
                'completion_rate': completion_rate,
            },
            'total_loans': total_loans,
        }
    
    @staticmethod
    def calculate_trend_analysis(loans_queryset, period_months=12):
        """Calculate loan trends over specified period."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_months * 30)
        
        # Monthly disbursement trends
        monthly_data = []
        current_date = start_date
        
        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
            
            month_loans = loans_queryset.filter(
                disbursement_date__range=[month_start, month_end]
            )
            
            month_metrics = month_loans.aggregate(
                count=Count('id'),
                amount=Sum(Coalesce('amount_approved', 'amount_requested')),
                avg_size=Avg(Coalesce('amount_approved', 'amount_requested'))
            )
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'loans_count': month_metrics['count'] or 0,
                'disbursed_amount': month_metrics['amount'] or Decimal('0.00'),
                'average_loan_size': month_metrics['avg_size'] or Decimal('0.00'),
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return monthly_data
    
    @staticmethod
    def calculate_loan_aging_analysis(loans_queryset):
        """Calculate loan aging analysis."""
        aging_buckets = {
            'current': {'min': 0, 'max': 0},
            '1-30_days': {'min': 1, 'max': 30},
            '31-60_days': {'min': 31, 'max': 60},
            '61-90_days': {'min': 61, 'max': 90},
            '91-180_days': {'min': 91, 'max': 180},
            'over_180_days': {'min': 181, 'max': 9999},
        }
        
        aging_analysis = {}
        total_outstanding = Decimal('0.00')
        
        for bucket_name in aging_buckets:
            aging_analysis[bucket_name] = {
                'count': 0,
                'outstanding_amount': Decimal('0.00'),
                'percentage': 0,
            }

        for loan in loans_queryset:
            days = loan.days_overdue
            if days == 0:
                bucket_name = 'current'
            elif 1 <= days <= 30:
                bucket_name = '1-30_days'
            elif 31 <= days <= 60:
                bucket_name = '31-60_days'
            elif 61 <= days <= 90:
                bucket_name = '61-90_days'
            elif 91 <= days <= 180:
                bucket_name = '91-180_days'
            else:
                bucket_name = 'over_180_days'

            aging_analysis[bucket_name]['count'] += 1
            aging_analysis[bucket_name]['outstanding_amount'] += (
                loan.outstanding_balance or Decimal('0.00')
            )
            total_outstanding += loan.outstanding_balance or Decimal('0.00')
        
        # Calculate percentages
        for bucket_name in aging_analysis:
            if total_outstanding > 0:
                aging_analysis[bucket_name]['percentage'] = (
                    aging_analysis[bucket_name]['outstanding_amount'] / total_outstanding * 100
                )
        
        return {
            'aging_buckets': aging_analysis,
            'total_outstanding': total_outstanding,
        }


class CollectionAnalytics:
    """Advanced collection performance analytics."""
    
    @staticmethod
    def calculate_collection_efficiency(collections_queryset, period_days=30):
        """Calculate collection efficiency metrics."""
        from apps.repayments.models import DailyCollection
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        period_collections = collections_queryset.filter(
            collection_date__range=[start_date, end_date]
        )
        
        # Overall metrics
        total_metrics = period_collections.aggregate(
            total_collected=Sum('total_amount'),
            total_target=Sum('target_amount'),
            total_payments=Sum('payment_count'),
            avg_efficiency=Avg('collection_efficiency'),
            collections_count=Count('id')
        )
        
        # Collector performance
        collector_performance = period_collections.values(
            'collector__first_name', 'collector__last_name'
        ).annotate(
            total_collected=Sum('total_amount'),
            total_target=Sum('target_amount'),
            avg_efficiency=Avg('collection_efficiency'),
            collections_count=Count('id'),
            total_payments=Sum('payment_count')
        ).order_by('-total_collected')
        
        # Daily trends
        daily_trends = []
        current_date = start_date
        while current_date <= end_date:
            day_collections = period_collections.filter(collection_date=current_date)
            day_metrics = day_collections.aggregate(
                total_collected=Sum('total_amount'),
                total_target=Sum('target_amount'),
                collections_count=Count('id')
            )
            
            daily_trends.append({
                'date': current_date,
                'date_str': current_date.strftime('%Y-%m-%d'),
                'total_collected': day_metrics['total_collected'] or Decimal('0.00'),
                'total_target': day_metrics['total_target'] or Decimal('0.00'),
                'collections_count': day_metrics['collections_count'] or 0,
                'efficiency': (
                    (day_metrics['total_collected'] / day_metrics['total_target'] * 100)
                    if day_metrics['total_target'] and day_metrics['total_target'] > 0
                    else 0
                )
            })
            
            current_date += timedelta(days=1)
        
        return {
            'period_metrics': total_metrics,
            'collector_performance': list(collector_performance),
            'daily_trends': daily_trends,
            'period_start': start_date,
            'period_end': end_date,
        }
    
    @staticmethod
    def calculate_payment_method_analysis(payments_queryset):
        """Analyze payment methods usage and efficiency."""
        from apps.repayments.models import Payment
        
        # Payment method breakdown
        method_analysis = payments_queryset.values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('amount'),
            avg_amount=Avg('amount')
        ).order_by('-total_amount')
        
        total_amount = payments_queryset.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Add percentages
        for method in method_analysis:
            if total_amount > 0:
                method['percentage'] = (method['total_amount'] / total_amount * 100)
            else:
                method['percentage'] = 0
        
        return {
            'method_breakdown': list(method_analysis),
            'total_amount': total_amount,
            'total_payments': payments_queryset.count(),
        }


class FinancialAnalytics:
    """Advanced financial analytics and ratios."""
    
    @staticmethod
    def calculate_financial_ratios(financial_data):
        """Calculate key financial ratios."""
        # Liquidity ratios
        current_ratio = (
            financial_data.get('current_assets', 0) / financial_data.get('current_liabilities', 1)
            if financial_data.get('current_liabilities', 0) > 0 else 0
        )
        
        quick_ratio = (
            (financial_data.get('current_assets', 0) - financial_data.get('inventory', 0)) /
            financial_data.get('current_liabilities', 1)
            if financial_data.get('current_liabilities', 0) > 0 else 0
        )
        
        # Profitability ratios
        net_profit_margin = (
            financial_data.get('net_income', 0) / financial_data.get('total_revenue', 1) * 100
            if financial_data.get('total_revenue', 0) > 0 else 0
        )
        
        return_on_assets = (
            financial_data.get('net_income', 0) / financial_data.get('total_assets', 1) * 100
            if financial_data.get('total_assets', 0) > 0 else 0
        )
        
        return_on_equity = (
            financial_data.get('net_income', 0) / financial_data.get('total_equity', 1) * 100
            if financial_data.get('total_equity', 0) > 0 else 0
        )
        
        # Efficiency ratios
        asset_turnover = (
            financial_data.get('total_revenue', 0) / financial_data.get('total_assets', 1)
            if financial_data.get('total_assets', 0) > 0 else 0
        )
        
        # Leverage ratios
        debt_to_equity = (
            financial_data.get('total_debt', 0) / financial_data.get('total_equity', 1)
            if financial_data.get('total_equity', 0) > 0 else 0
        )
        
        debt_to_assets = (
            financial_data.get('total_debt', 0) / financial_data.get('total_assets', 1)
            if financial_data.get('total_assets', 0) > 0 else 0
        )
        
        return {
            'liquidity_ratios': {
                'current_ratio': round(current_ratio, 2),
                'quick_ratio': round(quick_ratio, 2),
            },
            'profitability_ratios': {
                'net_profit_margin': round(net_profit_margin, 2),
                'return_on_assets': round(return_on_assets, 2),
                'return_on_equity': round(return_on_equity, 2),
            },
            'efficiency_ratios': {
                'asset_turnover': round(asset_turnover, 2),
            },
            'leverage_ratios': {
                'debt_to_equity': round(debt_to_equity, 2),
                'debt_to_assets': round(debt_to_assets, 2),
            }
        }
    
    @staticmethod
    def calculate_growth_rates(current_period, previous_period):
        """Calculate growth rates between periods."""
        growth_rates = {}
        
        for key in current_period:
            if key in previous_period:
                current_value = current_period[key] or 0
                previous_value = previous_period[key] or 0
                
                if previous_value > 0:
                    growth_rate = ((current_value - previous_value) / previous_value) * 100
                    growth_rates[key] = round(growth_rate, 2)
                else:
                    growth_rates[key] = 0
            else:
                growth_rates[key] = 0
        
        return growth_rates


class BorrowerAnalytics:
    """Advanced borrower analytics and segmentation."""
    
    @staticmethod
    def calculate_borrower_segmentation(borrowers_queryset):
        """Segment borrowers based on various criteria."""
        from apps.core.models import LoanStatusChoices
        today = timezone.now().date()
        
        # Age segmentation
        age_segments = {
            '18-25': borrowers_queryset.filter(
                date_of_birth__range=(
                    today - relativedelta(years=25),
                    today - relativedelta(years=18),
                )
            ).count(),
            '26-35': borrowers_queryset.filter(
                date_of_birth__range=(
                    today - relativedelta(years=35),
                    today - relativedelta(years=26),
                )
            ).count(),
            '36-45': borrowers_queryset.filter(
                date_of_birth__range=(
                    today - relativedelta(years=45),
                    today - relativedelta(years=36),
                )
            ).count(),
            '46-55': borrowers_queryset.filter(
                date_of_birth__range=(
                    today - relativedelta(years=55),
                    today - relativedelta(years=46),
                )
            ).count(),
            '56+': borrowers_queryset.filter(
                date_of_birth__lte=today - relativedelta(years=56)
            ).count(),
        }
        
        # Gender distribution
        gender_distribution = borrowers_queryset.values('gender').annotate(
            count=Count('id')
        )
        
        # Geographic distribution
        geographic_distribution = borrowers_queryset.values(
            'district', 'region'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Loan performance segmentation
        performance_segments = {
            'excellent': borrowers_queryset.filter(
                loans__status=LoanStatusChoices.COMPLETED
            ).distinct().count(),
            'good': borrowers_queryset.filter(
                loans__status__in=[LoanStatusChoices.ACTIVE, LoanStatusChoices.DISBURSED]
            ).distinct().count(),
            'poor': borrowers_queryset.filter(
                loans__is_npl=True
            ).distinct().count(),
            'defaulted': borrowers_queryset.filter(
                loans__status=LoanStatusChoices.DEFAULTED
            ).distinct().count(),
        }
        
        return {
            'age_segments': age_segments,
            'gender_distribution': list(gender_distribution),
            'geographic_distribution': list(geographic_distribution),
            'performance_segments': performance_segments,
            'total_borrowers': borrowers_queryset.count(),
        }


# Utility functions for data export
def prepare_data_for_export(queryset, fields):
    """Prepare queryset data for export."""
    data = []
    for obj in queryset:
        row = []
        for field in fields:
            if '.' in field:
                # Handle related field access
                value = obj
                for part in field.split('.'):
                    value = getattr(value, part, None)
                    if value is None:
                        break
            else:
                value = getattr(obj, field, None)
            
            row.append(value)
        data.append(row)
    
    return data


def format_currency(amount):
    """Format currency for display."""
    if isinstance(amount, Decimal):
        return f"Tsh {amount:,.2f}"
    elif isinstance(amount, (int, float)):
        return f"Tsh {amount:,.2f}"
    return str(amount)
