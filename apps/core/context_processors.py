"""Template context processors for shared application settings."""

from django.conf import settings


CURRENCY_SYMBOLS = {
    'TSH': 'Tsh. ',
    'TZS': 'Tsh. ',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'INR': '₹',
    'KES': 'KSh',
    'UGX': 'USh',
}


def currency_settings(request):
    """Expose the active system currency code and symbol to all templates."""
    currency_code = getattr(settings, 'DEFAULT_CURRENCY', 'USD')

    try:
        from apps.core.models import CompanyProfile, SystemSetting

        company = CompanyProfile.objects.filter(is_active=True).order_by('-updated_at').first()
        if company and company.base_currency:
            currency_code = company.base_currency
        else:
            setting = SystemSetting.objects.filter(key='default_currency', is_active=True).first()
            if setting and setting.value:
                currency_code = setting.value
    except Exception:
        pass

    currency_code = str(currency_code).strip().upper()
    return {
        'system_currency': currency_code,
        'currency_symbol': CURRENCY_SYMBOLS.get(currency_code, currency_code),
    }