"""
Performance optimization utilities.
"""

import time
import functools
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
import logging

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    def get_optimized_loans_queryset():
        """Get optimized loans queryset with select_related and prefetch_related."""
        from apps.loans.models import Loan
        
        return Loan.objects.select_related(
            'borrower',
            'loan_type',
            'created_by',
            'approved_by',
            'disbursed_by'
        ).prefetch_related(
            'repayment_schedules',
            'penalties',
            'disbursements'
        )
    
    @staticmethod
    def get_optimized_borrowers_queryset():
        """Get optimized borrowers queryset."""
        from apps.borrowers.models import Borrower
        
        return Borrower.objects.select_related(
            'created_by',
            'updated_by'
        ).prefetch_related(
            'loans',
            'savings_accounts',
            'group_memberships'
        )
    
    @staticmethod
    def get_optimized_savings_queryset():
        """Get optimized savings accounts queryset."""
        from apps.savings.models import SavingsAccount
        
        return SavingsAccount.objects.select_related(
            'borrower',
            'created_by'
        ).prefetch_related(
            'transactions'
        )


class CacheManager:
    """Cache management utilities."""
    
    CACHE_TIMEOUTS = {
        'dashboard_stats': 300,      # 5 minutes
        'loan_summary': 600,         # 10 minutes
        'borrower_count': 1800,      # 30 minutes
        'system_health': 60,         # 1 minute
        'user_permissions': 3600,    # 1 hour
    }
    
    @classmethod
    def get_cache_key(cls, key_type, *args):
        """Generate standardized cache keys."""
        if args:
            return f"microfinance:{key_type}:{':'.join(map(str, args))}"
        return f"microfinance:{key_type}"
    
    @classmethod
    def get_dashboard_stats(cls, user_id):
        """Get cached dashboard statistics."""
        cache_key = cls.get_cache_key('dashboard_stats', user_id)
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = cls._calculate_dashboard_stats(user_id)
            cache.set(cache_key, stats, cls.CACHE_TIMEOUTS['dashboard_stats'])
        
        return stats
    
    @classmethod
    def _calculate_dashboard_stats(cls, user_id):
        """Calculate dashboard statistics."""
        from apps.loans.models import Loan
        from apps.borrowers.models import Borrower
        from apps.savings.models import SavingsAccount
        from django.db.models import Sum, Count
        
        stats = {
            'total_loans': Loan.objects.count(),
            'active_loans': Loan.objects.filter(status='disbursed').count(),
            'total_borrowers': Borrower.objects.filter(status='active').count(),
            'total_savings': SavingsAccount.objects.aggregate(
                total=Sum('balance')
            )['total'] or 0,
            'outstanding_amount': Loan.objects.aggregate(
                total=Sum('outstanding_balance')
            )['total'] or 0,
        }
        
        return stats
    
    @classmethod
    def invalidate_dashboard_cache(cls, user_id=None):
        """Invalidate dashboard cache."""
        if user_id:
            cache_key = cls.get_cache_key('dashboard_stats', user_id)
            cache.delete(cache_key)
        else:
            # Invalidate all dashboard caches (expensive operation)
            cache.delete_pattern("microfinance:dashboard_stats:*")
    
    @classmethod
    def get_loan_summary(cls, loan_id):
        """Get cached loan summary."""
        cache_key = cls.get_cache_key('loan_summary', loan_id)
        summary = cache.get(cache_key)
        
        if summary is None:
            summary = cls._calculate_loan_summary(loan_id)
            cache.set(cache_key, summary, cls.CACHE_TIMEOUTS['loan_summary'])
        
        return summary
    
    @classmethod
    def _calculate_loan_summary(cls, loan_id):
        """Calculate loan summary."""
        from apps.loans.models import Loan
        from django.db.models import Sum
        
        try:
            loan = Loan.objects.select_related('borrower', 'loan_type').get(id=loan_id)
            
            repayments = loan.repayment_schedules.aggregate(
                total_paid=Sum('repayments__amount_paid'),
                total_due=Sum('amount_due')
            )
            
            summary = {
                'loan_number': loan.loan_number,
                'borrower_name': loan.borrower.get_full_name(),
                'amount_approved': loan.amount_approved,
                'outstanding_balance': loan.outstanding_balance,
                'total_paid': repayments['total_paid'] or 0,
                'total_due': repayments['total_due'] or 0,
                'status': loan.status,
            }
            
            return summary
            
        except Loan.DoesNotExist:
            return None


def cache_result(timeout=300, key_prefix=''):
    """Decorator to cache function results."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Calculate and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def monitor_db_queries(func):
    """Decorator to monitor database queries."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        initial_queries = len(connection.queries)
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        final_queries = len(connection.queries)
        
        query_count = final_queries - initial_queries
        execution_time = end_time - start_time
        
        if query_count > 10 or execution_time > 1.0:
            logger.warning(
                f"Performance warning: {func.__name__} executed {query_count} queries "
                f"in {execution_time:.2f} seconds"
            )
        
        return result
    return wrapper


class PerformanceMiddleware:
    """Middleware to monitor performance."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        initial_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        end_time = time.time()
        final_queries = len(connection.queries)
        
        # Calculate metrics
        execution_time = end_time - start_time
        query_count = final_queries - initial_queries
        
        # Add performance headers (only in debug mode)
        if settings.DEBUG:
            response['X-DB-Queries'] = str(query_count)
            response['X-Execution-Time'] = f"{execution_time:.3f}s"
        
        # Log slow requests
        if execution_time > 2.0 or query_count > 20:
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"({execution_time:.2f}s, {query_count} queries)"
            )
        
        return response


def optimize_queryset(queryset, select_related=None, prefetch_related=None):
    """Optimize queryset with select_related and prefetch_related."""
    if select_related:
        queryset = queryset.select_related(*select_related)
    
    if prefetch_related:
        queryset = queryset.prefetch_related(*prefetch_related)
    
    return queryset


class LazyLoader:
    """Lazy loading utility for expensive operations."""
    
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._result = None
        self._loaded = False
    
    def __call__(self):
        if not self._loaded:
            self._result = self.func(*self.args, **self.kwargs)
            self._loaded = True
        return self._result
    
    @property
    def result(self):
        return self()


def paginate_efficiently(queryset, page_size=25):
    """Efficient pagination for large querysets."""
    from django.core.paginator import Paginator
    
    # Use database-level pagination
    paginator = Paginator(queryset, page_size)
    
    # Add count optimization for large datasets
    if hasattr(queryset, 'count'):
        # Cache the count to avoid repeated COUNT queries
        count = cache.get(f"paginator_count_{hash(str(queryset.query))}")
        if count is None:
            count = queryset.count()
            cache.set(f"paginator_count_{hash(str(queryset.query))}", count, 300)
        paginator._count = count
    
    return paginator


def batch_process(queryset, batch_size=1000, callback=None):
    """Process large querysets in batches."""
    total_processed = 0
    
    while True:
        batch = list(queryset[total_processed:total_processed + batch_size])
        
        if not batch:
            break
        
        if callback:
            callback(batch)
        
        total_processed += len(batch)
        
        # Clear Django's query cache to prevent memory issues
        connection.queries_log.clear()
    
    return total_processed


# Decorators for view optimization
def cache_view(timeout=300):
    """Decorator to cache entire view responses."""
    return cache_page(timeout)


def vary_on_user(view_func):
    """Decorator to vary cache on user."""
    return vary_on_headers('Authorization')(view_func)


def require_ajax(view_func):
    """Decorator to require AJAX requests."""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'AJAX request required'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper


