from decimal import Decimal


DEFAULT_CURRENCY = "SGD"

RATES = {
    "SGD": Decimal("1.00"),
    "USD": Decimal("0.74"),
    "EUR": Decimal("0.68"),
}


def normalize_currency(value):
    if value in RATES:
        return value

    return DEFAULT_CURRENCY


def resolve_currency(request):
    if request.method == "POST":
        requested_currency = request.POST.get("currency")
    else:
        requested_currency = request.GET.get("currency")

    requested_currency = requested_currency or request.session.get(
        "currency",
        DEFAULT_CURRENCY,
    )

    return normalize_currency(requested_currency)


def get_selected_currency(request):
    selected_currency = resolve_currency(request)
    request.session["currency"] = selected_currency
    return selected_currency