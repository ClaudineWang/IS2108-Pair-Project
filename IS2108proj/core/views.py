from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .forms import CheckoutForm, CustomerReviewForm
from .models import (
    Product,
    Category,
    Cart,
    CartItem,
    CustomerProfile,
    Order,
    OrderItem,
    Review,
    SubscriptionBundle,
)
from .services import InsufficientStockError, place_order_from_cart


def product_list(request):
    """Displays searchable products and active subscription bundles."""
    search_query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    roast_level = request.GET.get("roast_level", "").strip()
    caffeine_type = request.GET.get("caffeine_type", "").strip()
    origin_country = request.GET.get("origin", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    filter_errors = []

    products = Product.objects.filter(is_visible=True).select_related(
        "category"
    ).order_by("name")
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(tasting_notes__icontains=search_query)
            | Q(origin_country__icontains=search_query)
        )
    if category_id:
        products = products.filter(category_id=category_id)
    if roast_level in dict(Product.ROAST_LEVEL):
        products = products.filter(roast_level=roast_level)
    if caffeine_type in dict(Product.CAFFEINE_TYPE):
        products = products.filter(caffeine_type=caffeine_type)
    if origin_country:
        products = products.filter(origin_country__iexact=origin_country)

    if min_price:
        try:
            min_price_value = Decimal(min_price)
            if not min_price_value.is_finite() or min_price_value < 0:
                raise InvalidOperation
            products = products.filter(price__gte=min_price_value)
        except (InvalidOperation, ValueError):
            filter_errors.append("Enter a valid minimum price.")
    if max_price:
        try:
            max_price_value = Decimal(max_price)
            if not max_price_value.is_finite() or max_price_value < 0:
                raise InvalidOperation
            products = products.filter(price__lte=max_price_value)
        except (InvalidOperation, ValueError):
            filter_errors.append("Enter a valid maximum price.")

    subscription_bundles = SubscriptionBundle.objects.filter(
        is_active=True
    ).prefetch_related("bundle_items__product").order_by("name")
    if search_query:
        subscription_bundles = subscription_bundles.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(customer=request.user).first()
        if cart:
            cart_count = sum(item.quantity for item in cart.items.all())

    context = {
        "products": products,
        "subscription_bundles": subscription_bundles,
        "categories": Category.objects.all().order_by("name"),
        "roast_levels": Product.ROAST_LEVEL,
        "caffeine_types": Product.CAFFEINE_TYPE,
        "origins": Product.objects.filter(
            is_visible=True
        ).exclude(origin_country="").values_list("origin_country", flat=True).distinct().order_by("origin_country"),
        "search_query": search_query,
        "selected_category": category_id,
        "selected_roast": roast_level,
        "selected_caffeine": caffeine_type,
        "selected_origin": origin_country,
        "min_price": min_price,
        "max_price": max_price,
        "filter_errors": filter_errors,
        "cart_count": cart_count,
    }
    return render(request, 'core/product_list.html', context)


def product_detail(request, product_id):
    """Displays a product and its reviews, allowing eligible customers to review it."""
    product = get_object_or_404(Product, id=product_id, is_visible=True)
    cart_count = 0
    can_review = False
    has_reviewed = False
    review_form = CustomerReviewForm()

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(customer=request.user)
        cart_count = sum(item.quantity for item in cart.items.all())

        has_purchased = OrderItem.objects.filter(
            product=product,
            order__customer__user=request.user,
        ).exclude(order__delivery_status='cancelled').exists()
        has_reviewed = Review.objects.filter(
            product=product,
            customer__user=request.user,
        ).exists()
        can_review = has_purchased and not has_reviewed

        if request.method == 'POST':
            if not has_purchased:
                messages.error(request, 'You can review this product after purchasing it.')
                return redirect('core:product_detail', product_id=product.id)
            if has_reviewed:
                messages.info(request, 'You have already reviewed this product.')
                return redirect('core:product_detail', product_id=product.id)

            review_form = CustomerReviewForm(request.POST)
            if review_form.is_valid():
                customer_profile, _ = CustomerProfile.objects.get_or_create(
                    user=request.user
                )
                review = review_form.save(commit=False)
                review.product = product
                review.customer = customer_profile
                review.save()
                messages.success(request, 'Thank you for reviewing this product.')
                return redirect('core:product_detail', product_id=product.id)

    context = {
        'product': product,
        'cart_count': cart_count,
        'reviews': product.reviews.filter(is_visible=True)
        .select_related('customer__user')
        .order_by('-created_at'),
        'can_review': can_review,
        'has_reviewed': has_reviewed,
        'review_form': review_form,
    }
    return render(request, 'core/product_detail.html', context)


@login_required
def add_to_cart(request, product_id):
    """Adds a product to the logged-in customer's cart."""
    product = get_object_or_404(Product, id=product_id, is_visible=True)

    quantity = request.POST.get('quantity', 1)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1

    if quantity <= 0:
        messages.error(request, 'Quantity must be at least 1.')
        return redirect('core:product_detail', product_id=product.id)

    cart, _ = Cart.objects.get_or_create(customer=request.user)
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()
    current_quantity = cart_item.quantity if cart_item else 0
    requested_quantity = current_quantity + quantity
    if requested_quantity > product.stock_level:
        messages.error(
            request,
            f"Only {product.stock_level} unit(s) of {product.name} are currently available.",
        )
        return redirect('core:product_detail', product_id=product.id)

    if cart_item is None:
        cart_item = CartItem(cart=cart, product=product)
    cart_item.quantity = requested_quantity

    cart_item.save()
    messages.success(request, f'{product.name} added to cart.')
    return redirect('core:product_detail', product_id=product.id)


@login_required
def cart_view(request):
    """Shows all cart items for the logged-in customer."""
    cart, _ = Cart.objects.get_or_create(customer=request.user)
    cart_items = cart.items.select_related('product').all()
    subtotal = sum((item.subtotal for item in cart_items), Decimal('0.00'))
    total_items = sum(item.quantity for item in cart_items)
    delivery_fee = Decimal('0.00') if subtotal >= Decimal('50.00') else Decimal('5.00')
    total = subtotal + delivery_fee
    cart_count = total_items

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total_items': total_items,
        'cart_count': cart_count,
        'delivery_fee': delivery_fee,
        'total': total,
    }
    return render(request, 'core/cart.html', context)


@login_required
@require_POST
def update_cart_item(request, item_id):
    """Updates the quantity of a cart item."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user)

    quantity = request.POST.get('quantity', cart_item.quantity)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = cart_item.quantity

    adjustment = request.POST.get('adjust_quantity')
    if adjustment == 'increase':
        quantity += 1
    elif adjustment == 'decrease':
        quantity -= 1

    quantity = max(quantity, 1)
    if cart_item.product.stock_level < 1:
        messages.error(
            request,
            f'{cart_item.product.name} is currently out of stock. Remove it from your cart to continue.',
        )
        return redirect('core:cart')
    if quantity > cart_item.product.stock_level:
        if adjustment == 'decrease':
            quantity = cart_item.product.stock_level
        else:
            messages.error(
                request,
                f'Only {cart_item.product.stock_level} unit(s) of '
                f'{cart_item.product.name} are currently available.',
            )
            return redirect('core:cart')

    cart_item.quantity = quantity
    cart_item.save()
    messages.success(request, f'{cart_item.product.name} quantity updated.')

    return redirect('core:cart')


@login_required
@require_POST
def remove_from_cart(request, item_id):
    """Removes a product from the user's cart."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.info(request, f'{product_name} removed from cart.')
    return redirect('core:cart')


@login_required
def checkout(request):
    """Shows the checkout page and creates an order when submitted."""
    cart, _ = Cart.objects.get_or_create(customer=request.user)
    cart_items = cart.items.select_related('product').all()

    if not cart_items:
        messages.info(request, 'Your cart is empty. Add a product before checking out.')
        return redirect('core:cart')

    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    subtotal = sum(item.subtotal for item in cart_items)
    delivery_fee = Decimal('0.00') if subtotal >= Decimal('50.00') else Decimal('5.00')
    total = subtotal + delivery_fee
    cart_count = sum(item.quantity for item in cart_items)
    form = CheckoutForm(
        request.POST if request.method == 'POST' else None,
        initial={"delivery_address": customer_profile.delivery_address},
    )
    if request.method == 'POST':
        for field_name in form.errors:
            form.fields[field_name].widget.attrs["aria-invalid"] = "true"

    if request.method == 'POST' and form.is_valid():
        try:
            order = place_order_from_cart(
                cart=cart,
                customer=customer_profile,
                delivery_address=form.cleaned_data['delivery_address'],
            )
        except InsufficientStockError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f'Order #{order.id} created successfully!')
            return redirect('customer:order_detail', order_id=order.id)

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'customer_profile': customer_profile,
        'cart_count': cart_count,
        'form': form,
    }
    return render(request, 'core/checkout.html', context)