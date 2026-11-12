from decimal import Decimal

from django.contrib.auth import login, logout
from django.db import models, transaction
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from adminpanel.forms import (
    AdminLoginForm,
    BundleItemForm,
    BundleItemFormSet,
    InventoryForm,
    OrderForm,
    ProductForm,
    ReviewForm,
    SubscriptionBundleForm,
)
from core.currency import RATES as CURRENCY_RATES, get_selected_currency
from core.forecasting import get_restock_predictions
from core.models import (
    BundleItem,
    Category,
    CustomerProfile,
    CustomerSubscription,
    Order,
    OrderItem,
    Product,
    Review,
    SubscriptionBundle,
)
from core.pagination import paginate_queryset
from core.services import advance_subscription_delivery
from .decorators import staff_required
@staff_required
def product_list(request):
    products = Product.objects.all().order_by('id')
    categories = Category.objects.all().order_by('name')
    search_query = request.GET.get("search", "")
    category_filter = request.GET.get("category", "")
    caffeine_filter = request.GET.get("caffeine_type", "")
    roast_filter = request.GET.get("roast_level", "")
    selected_currency = get_selected_currency(request)
    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    if search_query:
        products = products.filter(name__icontains=search_query)

    if category_filter:
        products = products.filter(category_id=category_filter)

    if caffeine_filter:
        products = products.filter(caffeine_type=caffeine_filter)

    if roast_filter:
        products = products.filter(roast_level=roast_filter)

    page_obj, query_string = paginate_queryset(request, products, per_page=10)

    for product in page_obj:
        product.display_price = product.price * CURRENCY_RATES[selected_currency]

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        'categories': categories,
        'search_query': search_query,
        'roast_levels': Product.ROAST_LEVEL,
        'caffeine_types': Product.CAFFEINE_TYPE,
        'category_filter': category_filter,
        'currency': selected_currency,
        'selected_currency': selected_currency,
    }

    return render(request, 'adminpanel/product_list.html', context)


@staff_required
def product_add(request):
    selected_currency = get_selected_currency(request)

    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    request.session["currency"] = selected_currency

    if request.method == "POST":
        form = ProductForm(
            request.POST,
            request.FILES,
            currency=selected_currency
        )

        if form.is_valid():
            form.save()

            return redirect(
                "adminpanel:product_list"
            )
    else:
        form = ProductForm(
            currency=selected_currency
        )

    context = {
        "form": form,
        "page_title": "Add New Product",
        "submit_button_text": "Add Product",
        "selected_currency": selected_currency,
    }

    return render(
        request,
        "adminpanel/product_form.html",
        context
    )
@staff_required
def product_update(request, product_id):
    product = Product.objects.get(id=product_id)

    selected_currency = get_selected_currency(request)



    if request.method == "POST":


        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product,
            currency=selected_currency
        )

        if form.is_valid():
            form.save()

            return redirect(
                "adminpanel:product_list"
            )
    else:
        form = ProductForm(
            instance=product,
            currency=selected_currency
        )

    return render(request, "adminpanel/product_form.html", {
        "form": form,
        "product": product,
        "page_title": "Update Product",
        "submit_button_text": "Update Product",
        "selected_currency": selected_currency,

    })

@staff_required
def inventory_list(request):
    products = Product.objects.all().order_by('id')
    categories = Category.objects.all().order_by('name')
    search_query = request.GET.get("search", "")
    category_filter = request.GET.get("category", "")
    stock_status_filter = request.GET.get("stock_status", "")
    selected_currency = get_selected_currency(request)
    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    if search_query:
        products = products.filter(
            name__icontains = search_query
        )
    if category_filter:
        products = products.filter(
            category_id = category_filter
        )
    if stock_status_filter == "Out of Stock":
        products = products.filter(
            stock_level=0
        )

    elif stock_status_filter == "Low in Stock":
        products = products.filter(
            stock_level__gt=0,
            stock_level__lte=models.F("reorder_threshold")
        )

    elif stock_status_filter == "In Stock":
        products = products.filter(
            stock_level__gt=models.F("reorder_threshold")
        )
    page_obj, query_string = paginate_queryset(request, products, per_page=10)


    context= {
            'products': page_obj,
            'page_obj': page_obj,
            'query_string': query_string,
            'categories': categories,
            'search_query': search_query,
            'stock_status_filter': stock_status_filter,
            'category_filter': category_filter,

    }

    return render(request, 'adminpanel/inventory_list.html', context)

@staff_required
def inventory_update(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:inventory_list')
    else:
        form = InventoryForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'page_title': 'Update Inventory',
        'submit_button_text': 'Update Inventory',
    }
    return render(request, 'adminpanel/inventory_form.html', context)

@staff_required
def order_list(request):
    delivery_statuses = Order.DELIVERY_STATUS
    orders = Order.objects.all().order_by("-created_at")
    search_query = request.GET.get("search", "")
    date_filter = request.GET.get("created_at", "")
    order_type_filter = request.GET.get("order_type", "")
    delivery_status_filter = request.GET.get("delivery_status", "")
    selected_currency = get_selected_currency(request)
    if selected_currency not in CURRENCY_RATES:
        selected_currency= "SGD"

    if search_query:
        search_filter = (
            Q(customer__user__first_name__icontains=search_query) |
            Q(customer__user__last_name__icontains=search_query) |
            Q(customer__user__username__icontains=search_query)
        )
        if search_query.isdigit():
            search_filter |= Q(id=int(search_query))
        orders = orders.filter(search_filter)
    if date_filter:
        orders = orders.filter(
            created_at__date=date_filter
        )
    if order_type_filter:
        orders = orders.filter(
            order_type=order_type_filter
        )
    if delivery_status_filter:
        orders = orders.filter(
            delivery_status=delivery_status_filter
        )
    page_obj, query_string = paginate_queryset(request, orders, per_page=20)
    for order in page_obj:
        order.display_grand_total = order.grand_total * CURRENCY_RATES[selected_currency]

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        'delivery_statuses': delivery_statuses,
        'search_query': search_query,
        'date_filter': date_filter,
        'order_type_filter': order_type_filter,
        'delivery_status_filter': delivery_status_filter,
        'currency': selected_currency,
        'selected_currency': selected_currency,
    }
    return render(request, 'adminpanel/order_list.html', context)

@staff_required
def order_update(request, order_id):
    order = Order.objects.prefetch_related("items__product").get(id=order_id)

    selected_currency = get_selected_currency(request)

    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    request.session["currency"] = selected_currency

    if request.method == "POST":
        selected_currency = request.POST.get(
            "currency",
            request.session.get("currency", "SGD")
        )
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            previous_status = order.delivery_status
            form = OrderForm(request.POST, instance=order)

            if form.is_valid():
                updated_order = form.save()
                if (
                    previous_status != "cancelled"
                    and updated_order.delivery_status == "cancelled"
                ):
                    for item in order.items.all():
                        Product.objects.filter(pk=item.product_id).update(
                            stock_level=models.F("stock_level") + item.quantity
                        )
                if (
                    previous_status != "delivered"
                    and updated_order.delivery_status == "delivered"
                    and updated_order.subscription
                ):
                    advance_subscription_delivery(updated_order.subscription)
                return redirect("adminpanel:order_list")
    else:
        form = OrderForm(instance=order)

    for item in order.items.all():
        item.display_price_at_purchase = item.price_at_purchase * CURRENCY_RATES[selected_currency]
        item.display_subtotal = item.subtotal * CURRENCY_RATES[selected_currency]

    order.display_total_amount = order.total_amount * CURRENCY_RATES[selected_currency]
    order.display_delivery_fee = order.delivery_fee * CURRENCY_RATES[selected_currency]
    order.display_grand_total = order.grand_total * CURRENCY_RATES[selected_currency]

    context = {
        "form": form,
        "order": order,
        "page_title": f"Update Order {order.id}",
        "submit_button_text": "Update Order",
        "selected_currency": selected_currency,
    }
    return render(request, "adminpanel/order_form.html", context)

@staff_required
def customer_list(request):
    selected_currency = get_selected_currency(request)
    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    customers = (
        CustomerProfile.objects
        .select_related("user")
        .annotate(
            total_order=Count("orders", distinct=True),
            total_spending=Coalesce(
                models.Sum("orders__grand_total"),
                Decimal("0"),
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            ),
        )
        .order_by("id")
    )

    search_query = request.GET.get("search", "").strip()
    if search_query:
        search_filter = (
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
        if search_query.isdigit():
            search_filter |= Q(id=int(search_query))
        customers = customers.filter(search_filter)
    page_obj, query_string = paginate_queryset(request, customers, per_page=20)

    for customer in page_obj:
        customer.display_total_spending = (
            customer.total_spending or Decimal("0")
        ) * CURRENCY_RATES[selected_currency]

    context = {
        "customers": page_obj,
        'page_obj': page_obj,
        'quer_string': query_string,
        "search_query": search_query,
        "selected_currency": selected_currency,
        "page_title": "Customer List",
        "currency": selected_currency,
    }
    return render(request, "adminpanel/customer_list.html", context)

@staff_required
def customer_view (request, customer_id):
    selected_currency = get_selected_currency(request)

    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    request.session["currency"] = selected_currency

    customer = CustomerProfile.objects.annotate(
        total_order=Count('orders', distinct=True),
        total_spending=Coalesce(models.Sum('orders__grand_total'), 0, output_field=models.DecimalField(max_digits=10, decimal_places=2))
    ).select_related('user').get(id=customer_id)

    customer_recent_orders = customer.orders.select_related("customer").prefetch_related("items__product").order_by("-created_at")[:5]

    for order in customer_recent_orders:
        order.display_grand_total = order.grand_total * CURRENCY_RATES[selected_currency]

    customer.display_total_spending = customer.total_spending * CURRENCY_RATES[selected_currency]

    context = {
        'customer': customer,
        'page_title': 'Customer Details',
        'customer_recent_orders': customer_recent_orders,
        'selected_currency': selected_currency,
        'currency': selected_currency,
    }
    return render(request, 'adminpanel/customer_view.html', context)
@staff_required
def subscription_bundle_list(request):
    selected_currency = get_selected_currency(request)
    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    billing_frequencies = SubscriptionBundle.BILLING_FREQUENCY
    subscription_bundles = SubscriptionBundle.objects.all().order_by('id')
    search_query = request.GET.get("search", "")
    billing_frequency_filter = request.GET.get("billing_frequency", "")
    is_active_filter = request.GET.get("is_active", "").strip()

    if search_query:
        subscription_bundles = subscription_bundles.filter(
                name__icontains = search_query
            )

    if billing_frequency_filter:
       subscription_bundles = subscription_bundles.filter(
            billing_frequency=billing_frequency_filter
            )
    if is_active_filter == 'true':
        subscription_bundles = subscription_bundles.filter(is_active = True)
    elif is_active_filter == 'false':
        subscription_bundles = subscription_bundles.filter(is_active = False)

    page_obj, query_string = paginate_queryset(request, subscription_bundles, per_page=20)
    for bundle in page_obj:
        bundle.display_price = bundle.price_per_delivery * CURRENCY_RATES[selected_currency]
    context= {
        'subscription_bundles': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        'billing_frequencies': billing_frequencies,
        'search_query': search_query,
        'billing_frequency_filter': billing_frequency_filter,
        'is_active_filter': is_active_filter,
        'selected_currency': selected_currency,
        'currency': selected_currency,
    }
    return render(request, 'adminpanel/subscription_bundle_list.html', context)

@staff_required
def subscription_bundle_update(request, subscription_bundle_id):
    selected_currency = get_selected_currency(request)
    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    request.session["currency"] = selected_currency
    subscription_bundle = SubscriptionBundle.objects.get(id=subscription_bundle_id)

    if request.method == "POST":

        subscription_bundle_form = SubscriptionBundleForm(
            request.POST,
            instance=subscription_bundle,
            currency=selected_currency
        )
        bundle_item_formset = BundleItemFormSet(
            request.POST,
            instance=subscription_bundle,
            bundle=subscription_bundle
        )

        if (
            subscription_bundle_form.is_valid()
            and bundle_item_formset.is_valid()
        ):
            subscription_bundle_form.save()
            bundle_item_formset.save()

            return redirect(
                "adminpanel:subscription_bundle_list"
            )
    else:
        subscription_bundle_form = SubscriptionBundleForm(
            instance=subscription_bundle,
            currency=selected_currency
        )
        bundle_item_formset = BundleItemFormSet(
            instance=subscription_bundle,
            bundle=subscription_bundle
        )

    context = {
        "subscription_bundle_form": subscription_bundle_form,
        "bundle_item_formset": bundle_item_formset,
        "page_title": "Update Subscription Bundle",
        "submit_button_text": "Update Bundle",
        "selected_currency": selected_currency,
        'currency': selected_currency,
    }
    return render(request, "adminpanel/subscription_bundle_form.html", context)

@staff_required
def subscription_bundle_add(request):
    selected_currency = get_selected_currency(request)

    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    request.session["currency"] = selected_currency

    if request.method == "POST":


        subscription_bundle_form = SubscriptionBundleForm(
            request.POST,
            currency=selected_currency
        )
        bundle_item_formset = BundleItemFormSet(
            request.POST
        )

        if (
            subscription_bundle_form.is_valid()
            and bundle_item_formset.is_valid()
        ):
            subscription_bundle = subscription_bundle_form.save()
            bundle_item_formset.instance = subscription_bundle
            bundle_item_formset.save()
            return redirect("adminpanel:subscription_bundle_list")
    else:
        subscription_bundle_form = SubscriptionBundleForm(
            currency=selected_currency
        )
        bundle_item_formset = BundleItemFormSet()

    context = {
        "subscription_bundle_form": subscription_bundle_form,
        "bundle_item_formset": bundle_item_formset,
        "page_title": "Add New Subscription Bundle",
        "submit_button_text": "Add Bundle",
        "selected_currency": selected_currency,
    }
    return render(request, "adminpanel/subscription_bundle_form.html", context)

@staff_required
def review_list(request):
    reviews = Review.objects.all().order_by('rating')
    search_query = request.GET.get("search", "").strip()
    rating_filter = request.GET.get("rating", "")
    date_filter = request.GET.get("created_at", "")
    is_visible_filter = request.GET.get("is_visible", "")
    if search_query:
        search_filter = (
            Q(customer__user__first_name__icontains=search_query) |
            Q(customer__user__last_name__icontains=search_query) |
            Q(customer__user__username__icontains=search_query) |
            Q(product__name__icontains=search_query)
        )
        reviews = reviews.filter(search_filter)
    if rating_filter:
        reviews = reviews.filter(
            rating=rating_filter
        )
    if date_filter:
        reviews = reviews.filter(
            created_at__date=date_filter
        )
    if is_visible_filter:
        reviews = reviews.filter(
            is_visible=is_visible_filter
        )
    page_obj, query_string = paginate_queryset(request, reviews, per_page=10)
    context = {
        'reviews': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        'rating_choices': Review.RATING_CHOICES,
        'search_query': search_query,
        'rating_filter': rating_filter,
        'date_filter': date_filter,
        'is_visible_filter': is_visible_filter
    }
    return render(request, 'adminpanel/review_list.html', context)

@staff_required
def review_update(request, review_id):
    review = Review.objects.get(id=review_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            return redirect('adminpanel:review_list')
    else:
        form = ReviewForm(instance=review)

    context = {
        'form': form,
        'review': review,
        'page_title': f'Update Review {review.id}',
        'submit_button_text': 'Update Status',
    }
    return render(request, 'adminpanel/review_form.html', context)

@staff_required
def customer_subscription_list(request):
    selected_currency = get_selected_currency(request)

    subscriptions = CustomerSubscription.objects.select_related('customer', 'bundle').order_by('-start_date')
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    if search_query:
        search_filter = (
            Q(customer__user__first_name__icontains=search_query) |
            Q(customer__user__last_name__icontains=search_query) |
            Q(customer__user__username__icontains=search_query) |
            Q(bundle__name__icontains=search_query)
        )
        subscriptions = subscriptions.filter(search_filter)
    if status_filter:
        subscriptions = subscriptions.filter(
            status = status_filter
        )
    page_obj, query_string = paginate_queryset(request, subscriptions, per_page=20)

    context = {
        'subscriptions': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        'status_choices': CustomerSubscription.STATUS_CHOICES,
        'search_query': search_query,
        'status_filter': status_filter,
        'selected_currency': selected_currency,
        'currency': selected_currency,
    }
    return render(request, 'adminpanel/customer_subscription_list.html', context)

@staff_required
def customer_subscription_view(request, subscription_id):
    selected_currency = get_selected_currency(request)

    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"



    subscription = (
        CustomerSubscription.objects
        .select_related("customer__user", "bundle")
        .get(id=subscription_id)
    )


    subscription.bundle.display_price = (
        subscription.bundle.price_per_delivery * CURRENCY_RATES[selected_currency]
    ).quantize(Decimal("0.01"))

    context = {
        "subscription": subscription,
        "page_title": "Customer Subscription Details",
        "selected_currency": selected_currency,
        "currency": selected_currency,
    }
    return render(request, "adminpanel/customer_subscription_view.html", context)

def admin_login(request):
    if request.method == "POST":
        form = AdminLoginForm(request.POST)

        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            return redirect("adminpanel:admin_dashboard")
    else:
        form = AdminLoginForm()

    return render(request, "adminpanel/admin_login.html", {
        "form": form,
        "page_title": "Admin Login",
    })

@require_POST
@staff_required
def admin_logout(request):
    logout(request)
    return redirect("adminpanel:admin_dashboard")

@staff_required
def admin_dashboard(request):
    selected_currency = get_selected_currency(request)
    conversion_rate = CURRENCY_RATES.get(selected_currency, 1.0)
    money_field = models.DecimalField(max_digits=12, decimal_places=2)
    def convert_money(value):
        value = value or Decimal("0.00")
        return (value * Decimal(conversion_rate)).quantize(Decimal("0.01"))
    valid_orders = Order.objects.filter(delivery_status__in=["pending", "roasting", "shipped", "delivered"])
    total_orders = valid_orders.aggregate(revenue=Coalesce(Sum("grand_total"), Decimal("0.00"), output_field=money_field),
                                          product_sales=Coalesce(Sum("items__price_at_purchase"), Decimal("0.00"), output_field=money_field),
                                          delivery_fees=Coalesce(Sum("delivery_fee"), Decimal("0.00"), output_field=money_field))
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(stock_level__lte=F("reorder_threshold")).order_by("stock_level")
    out_of_stock_products = Product.objects.filter(stock_level=0).order_by("name")
    top_products = list( OrderItem.objects.exclude(order__delivery_status="cancelled")
        .values("product__id", "product__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:5]
    )
    popular_bundles = list( CustomerSubscription.objects.filter(status="active").values("bundle__id", "bundle__name")
        .annotate(active_subscriptions=Count("id"))
        .order_by("-active_subscriptions")[:5]
    )
    recent_orders = valid_orders.select_related("customer__user").prefetch_related("items__product").order_by("-created_at")[:5]
    for order in recent_orders:
        order.display_grand_total = convert_money(order.grand_total)
    monthly_revenue = ( valid_orders.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(monthly_revenue=Coalesce(Sum("grand_total"), Decimal("0.00"), output_field=money_field))
        .order_by("month")
    )
    monthly_revenue_data = []
    for entry in monthly_revenue:
        month = entry["month"].strftime("%B %Y")
        revenue = convert_money(entry["monthly_revenue"])
        monthly_revenue_data.append({"month": month, "revenue": revenue})
    context = {
        'selected_currency': selected_currency,
        'currency': selected_currency,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'top_products': top_products,
        'total_orders': valid_orders.count(),
        'popular_bundles': popular_bundles,
        'recent_orders': recent_orders,
        'delivery_fees': convert_money(total_orders["delivery_fees"]),
        'product_sales': convert_money(total_orders["product_sales"]),
        'total_revenue': convert_money(total_orders["revenue"]),
        'monthly_revenue_data': monthly_revenue_data,
        'total_customers': CustomerProfile.objects.count(),
        'active_subscriptions': CustomerSubscription.objects.filter(status="active").count(),
    }
    return render(request, "adminpanel/admin_dashboard.html", context)

#ML model prediction view
@staff_required
def predictions(request):
    selected_currency = get_selected_currency(request)
    if selected_currency not in CURRENCY_RATES:
        selected_currency = "SGD"

    predictions = get_restock_predictions()
    def urgency_rank(prediction):
        if prediction["stock_status"] == "Out of Stock":
            return 0

        if prediction["suggested_restock"] > 0:
            return 1

        if prediction["stock_status"] == "Low in Stock":
            return 2

        return 3
    predictions.sort(key=lambda prediction: (
            urgency_rank(prediction),
            -prediction["suggested_restock"],
            -prediction["predicted_demand"],
            prediction["product_name"].lower(),
        )
    )
    page_obj, query_string = paginate_queryset(
        request,
        predictions,
        per_page=10
    )

    context = {
        "predictions": page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        "selected_currency": selected_currency,
        "currency": selected_currency,
    }
    return render(request, "adminpanel/predictions.html", context)
