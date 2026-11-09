from decimal import Decimal
from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from adminpanel.forms import OrderForm, ProductForm, InventoryForm, SubscriptionBundleForm, BundleItemForm, BundleItemFormSet, ReviewForm, AdminLoginForm
from core.models import Order, Product, Category, CustomerProfile, SubscriptionBundle, BundleItem, Review, CustomerSubscription
from django.db import models
from django.db.models import Q, Count
from django.db.models.functions import Coalesce
from core.services import advance_subscription_delivery
from core.currency import RATES as CURRENCY_RATES, get_selected_currency
from django.views.decorators.http import require_POST



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

    for product in products:
        product.display_price = product.price * CURRENCY_RATES[selected_currency]

    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'roast_levels': Product.ROAST_LEVEL_CHOICES,
        'caffeine_types': Product.CAFFEINE_TYPE_CHOICES,
        'category_filter': category_filter,
        'currency': selected_currency,
        'selected_currency': selected_currency,
    }

    return render(request, 'adminpanel/product_list.html', context)



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
def product_update(request, product_id):
    product = Product.objects.get(id=product_id)

    selected_currency = get_selected_currency(request)



    if request.method == "POST":


        form = ProductForm(
            request.POST,
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


    context= {
            'products': products,
            'categories': categories,
            'search_query': search_query,
            'stock_status_filter': stock_status_filter,
            'category_filter': category_filter,

    }

    return render(request, 'adminpanel/inventory_list.html', context)

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
    for order in orders:
        order.display_grand_total = order.grand_total * CURRENCY_RATES[selected_currency]

    context = {
        'orders': orders,
        'delivery_statuses': delivery_statuses,
        'search_query': search_query,
        'date_filter': date_filter,
        'order_type_filter': order_type_filter,
        'delivery_status_filter': delivery_status_filter,
        'currency': selected_currency,
        'selected_currency': selected_currency,
    }
    return render(request, 'adminpanel/order_list.html', context)

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
        form = OrderForm(request.POST, instance=order)

        if form.is_valid():
            updated_order = form.save()
            if (
                order.delivery_status != "delivered"
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

    for customer in customers:
        customer.display_total_spending = (
            customer.total_spending or Decimal("0")
        ) * CURRENCY_RATES[selected_currency]

    context = {
        "customers": customers,
        "search_query": search_query,
        "selected_currency": selected_currency,
        "page_title": "Customer List",
        "currency": selected_currency,
    }
    return render(request, "adminpanel/customer_list.html", context)

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
    for bundle in subscription_bundles:
        bundle.display_price = bundle.price_per_delivery * CURRENCY_RATES[selected_currency]
    context= {
        'subscription_bundles': subscription_bundles,
        'billing_frequencies': billing_frequencies,
        'search_query': search_query,
        'billing_frequency_filter': billing_frequency_filter,
        'is_active_filter': is_active_filter,
        'selected_currency': selected_currency,
        'currency': selected_currency,
    }
    return render(request, 'adminpanel/subscription_bundle_list.html', context)

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
    context = {
        'reviews': reviews,
        'rating_choices': Review.RATING_CHOICES,
        'search_query': search_query,
        'rating_filter': rating_filter,
        'date_filter': date_filter,
        'is_visible_filter': is_visible_filter
    }
    return render(request, 'adminpanel/review_list.html', context)

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

    context = {
        'subscriptions': subscriptions,
        'status_choices': CustomerSubscription.STATUS_CHOICES,
        'search_query': search_query,
        'status_filter': status_filter,
        'selected_currency': selected_currency,
        'currency': selected_currency,
    }
    return render(request, 'adminpanel/customer_subscription_list.html', context)

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
            return redirect("adminpanel:product_list")
    else:
        form = AdminLoginForm()

    return render(request, "adminpanel/admin_login.html", {
        "form": form,
        "page_title": "Admin Login",
    })

@require_POST
def admin_logout(request):
    logout(request)
    return redirect("adminpanel:admin_login")