from .currency import RATES, get_selected_currency


def currency(request):
    selected_currency = get_selected_currency(request)
    return {
        "selected_currency": selected_currency,
        "currency_rate": RATES[selected_currency],
    }