from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from apps.accounts.models import UserRole


class RoleAccessMiddleware(MiddlewareMixin):
    """Restrict sensitive sections to administrators only."""

    LOAN_OFFICER_ALLOWED_PATHS = (
        '/finance/income/add/',
        '/finance/expenditure/add/',
    )

    MANAGER_ALLOWED_PREFIXES = (
        '/users/',
        '/settings/',
        '/payroll/',
        '/financial-statements/',
        '/finance/',
    )

    ADMIN_ONLY_PREFIXES = (
        '/settings/',
        '/payroll/',
        '/financial-statements/',
        '/finance/api/',
        '/finance/shareholders/',
        '/finance/capital/',
        '/finance/retained-earnings/',
        '/finance/income/',
        '/finance/expenditure/',
        '/finance/expenditures/',
        '/finance/categories/',
    )

    ADMIN_ONLY_EXACT = (
        '/finance/',
    )

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        role = getattr(request.user, 'role', None)

        if any([
            getattr(request.user, 'is_superuser', False),
            getattr(request.user, 'is_admin_or_manager', False),
        ]):
            return None

        if role == UserRole.MANAGER:
            path = request.path
            if any(path.startswith(prefix) for prefix in self.MANAGER_ALLOWED_PREFIXES):
                return None

        path = request.path

        if getattr(request.user, 'is_officer_or_accountant', False) and path in self.LOAN_OFFICER_ALLOWED_PATHS:
            return None

        if path in self.ADMIN_ONLY_EXACT or any(path.startswith(prefix) for prefix in self.ADMIN_ONLY_PREFIXES):
            messages.error(request, 'Only administrators can access this section.')
            return redirect(reverse('core:dashboard'))

        return None


