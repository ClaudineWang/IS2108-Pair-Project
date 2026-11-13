from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def currency_amount(value, rate):
    try:
        return Decimal(str(value)) * Decimal(str(rate))
    except (InvalidOperation, TypeError, ValueError):
        return value