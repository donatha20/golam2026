from decimal import Decimal
from django import template

register = template.Library()

@register.filter
def percentage(value, total):
    """Calculate percentage of value relative to total."""
    try:
        if Decimal(str(total)) == 0:
            return 0
        return (Decimal(str(value)) / Decimal(str(total))) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
