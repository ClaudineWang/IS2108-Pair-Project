from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Category, Cart, CartItem, CustomerProfile, Order, OrderItem


def product_list(request):
    """Displays a list of all visible products, with optional category filtering."""
    category_id = request.GET.get('category')
    categories = Category.objects.all()

    if category_id:
        products = Product.objects.filter(category_id=category_id, is_visible=True)
    else:
        products = Product.objects.filter(is_visible=True)

    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(customer=request.user)
        cart_count = cart.items.count()

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_id,
        'cart_count': cart_count,
    }
    return render(request, 'core/product_list.html', context)


def product_detail(request, product_id):
    """Displays details for a single product."""
    product = get_object_or_404(Product, id=product_id, is_visible=True)
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(customer=request.user)
        cart_count = cart.items.count()

    context = {
        'product': product,
        'cart_count': cart_count,
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
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if created:
        cart_item.quantity = quantity
    else:
        cart_item.quantity += quantity

    cart_item.save()
    messages.success(request, f'{product.name} added to cart.')
    return redirect('core:product_detail', product_id=product.id)


@login_required
def cart_view(request):
    """Shows all cart items for the logged-in customer."""
    cart, _ = Cart.objects.get_or_create(customer=request.user)
    cart_items = cart.items.select_related('product').all()
    subtotal = sum(item.quantity * item.product.price for item in cart_items)
    total_items = sum(item.quantity for item in cart_items)

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total_items': total_items,
    }
    return render(request, 'core/cart.html', context)


@login_required
def update_cart_item(request, item_id):
    """Updates the quantity of a cart item."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user)

    quantity = request.POST.get('quantity', cart_item.quantity)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = cart_item.quantity

    if quantity <= 0:
        cart_item.delete()
        messages.info(request, f'{cart_item.product.name} removed from cart.')
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f'{cart_item.product.name} quantity updated.')

    return redirect('core:cart')


@login_required
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
    delivery_fee = 0 if subtotal >= 50 else 5.00
    total = subtotal + delivery_fee

    if request.method == 'POST':
        delivery_address = request.POST.get('delivery_address', '').strip()
        order_type = request.POST.get('order_type', 'one-time')

        if not delivery_address:
            delivery_address = customer_profile.delivery_address.strip()

        if not delivery_address:
            messages.error(request, 'Please provide a delivery address before placing your order.')
            return render(request, 'core/checkout.html', {
                'cart_items': cart_items,
                'subtotal': subtotal,
                'delivery_fee': delivery_fee,
                'total': total,
                'customer_profile': customer_profile,
            })

        order = Order.objects.create(
            customer=customer_profile,
            order_type=order_type,
            total_amount=subtotal,
            delivery_address=delivery_address,
            delivery_status='pending',
            delivery_fee=delivery_fee,
            grand_total=total,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_purchase=item.product.price,
            )

        cart.items.all().delete()
        messages.success(request, f'Order #{order.id} created successfully!')
        return redirect('core:product_list')

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'customer_profile': customer_profile,
    }
    return render(request, 'core/checkout.html', context)