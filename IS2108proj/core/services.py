from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from .models import (
    BundleItem,
    Cart,
    CustomerProfile,
    CustomerSubscription,
    Order,
    OrderItem,
    Product,
    SubscriptionBundle,
)


class InsufficientStockError(Exception):
    pass


@transaction.atomic
def place_order_from_cart(cart, customer, delivery_address):
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    cart_items = list(
        cart.items.select_for_update()
        .select_related("product")
        .order_by("product_id")
    )
    if not cart_items:
        raise InsufficientStockError("Your cart is empty. Add items before checking out.")

    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=[item.product_id for item in cart_items])
        .order_by("pk")
    }
    unavailable_items = [
        f"{item.product.name} (available: "
        f"{products[item.product_id].stock_level if item.product_id in products else 0})"
        for item in cart_items
        if item.product_id not in products
        or not products[item.product_id].is_visible
        or products[item.product_id].stock_level < item.quantity
    ]
    if unavailable_items:
        raise InsufficientStockError(
            "Some items are unavailable in the requested quantities: "
            + ", ".join(unavailable_items)
            + ". Review your cart and try again."
        )

    subtotal = sum(
        (products[item.product_id].price * item.quantity for item in cart_items),
        Decimal("0.00"),
    )
    delivery_fee = Decimal("0.00") if subtotal >= Decimal("50.00") else Decimal("5.00")
    order = Order.objects.create(
        customer=customer,
        order_type="one-time",
        total_amount=subtotal,
        delivery_address=delivery_address,
        delivery_status="pending",
        delivery_fee=delivery_fee,
        grand_total=subtotal + delivery_fee,
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                product=products[item.product_id],
                quantity=item.quantity,
                price_at_purchase=products[item.product_id].price,
            )
            for item in cart_items
        ]
    )
    for item in cart_items:
        product = products[item.product_id]
        product.stock_level -= item.quantity
        product.save(update_fields=["stock_level"])
    cart.items.all().delete()
    return order


@transaction.atomic
def start_subscription(bundle, customer, delivery_address):
    customer = CustomerProfile.objects.select_for_update().get(pk=customer.pk)
    bundle = SubscriptionBundle.objects.select_for_update().get(
        pk=bundle.pk,
        is_active=True,
    )
    if CustomerSubscription.objects.filter(
        customer=customer,
        bundle=bundle,
        status="active",
    ).exists():
        raise InsufficientStockError("You already have an active subscription to this bundle.")

    bundle_items = list(
        BundleItem.objects.select_for_update()
        .filter(subscription_bundle=bundle)
        .select_related("product")
        .order_by("product_id")
    )
    if not bundle_items:
        raise InsufficientStockError("This bundle is not ready for enrollment yet.")

    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=[item.product_id for item in bundle_items])
        .order_by("pk")
    }
    unavailable_items = [
        f"{item.product.name} (available: "
        f"{products[item.product_id].stock_level if item.product_id in products else 0})"
        for item in bundle_items
        if item.product_id not in products
        or not products[item.product_id].is_visible
        or products[item.product_id].stock_level < item.quantity
    ]
    if unavailable_items:
        raise InsufficientStockError(
            "This bundle is currently unavailable in the required quantities: "
            + ", ".join(unavailable_items)
            + ". Please try again later."
        )

    today = timezone.localdate()
    next_delivery_date = today + (
        relativedelta(years=1)
        if bundle.billing_frequency == "yearly"
        else relativedelta(months=1)
    )
    subscription = CustomerSubscription.objects.create(
        customer=customer,
        bundle=bundle,
        next_delivery_date=next_delivery_date,
    )
    order = Order.objects.create(
        customer=customer,
        subscription=subscription,
        order_type="subscription",
        total_amount=bundle.price_per_delivery,
        delivery_address=delivery_address,
        delivery_fee=Decimal("0.00"),
        grand_total=bundle.price_per_delivery,
    )

    retail_total = sum(
        (products[item.product_id].price * item.quantity for item in bundle_items),
        Decimal("0.00"),
    )
    if retail_total == 0:
        retail_total = Decimal(sum(item.quantity for item in bundle_items))
    bundle_price_cents = int(bundle.price_per_delivery * 100)
    line_allocations = []
    allocated_cents = 0
    for item in bundle_items:
        retail_value = products[item.product_id].price * item.quantity
        if retail_value == 0 and all(
            products[bundle_item.product_id].price == 0
            for bundle_item in bundle_items
        ):
            retail_value = Decimal(item.quantity)
        exact_cents = Decimal(bundle_price_cents) * retail_value / retail_total
        line_cents = int(exact_cents)
        line_allocations.append([item, line_cents, exact_cents - line_cents])
        allocated_cents += line_cents

    for allocation in sorted(line_allocations, key=lambda row: row[2], reverse=True):
        if allocated_cents >= bundle_price_cents:
            break
        allocation[1] += 1
        allocated_cents += 1

    order_items = []
    for item, line_cents, _ in line_allocations:
        base_cents, extra_units = divmod(line_cents, item.quantity)
        if item.quantity > extra_units:
            order_items.append(
                OrderItem(
                    order=order,
                    product=products[item.product_id],
                    quantity=item.quantity - extra_units,
                    price_at_purchase=Decimal(base_cents) / 100,
                )
            )
        if extra_units:
            order_items.append(
                OrderItem(
                    order=order,
                    product=products[item.product_id],
                    quantity=extra_units,
                    price_at_purchase=Decimal(base_cents + 1) / 100,
                )
            )
        product = products[item.product_id]
        product.stock_level -= item.quantity
        product.save(update_fields=["stock_level"])
    OrderItem.objects.bulk_create(order_items)
    return subscription, order


def calculate_grand_total(order):
    total = Decimal('0.00')
    for item in order.items.all():
        total += item.subtotal
    order.total_amount = total
    order.grand_total = total + order.delivery_fee
    
    order.save(
        update_fields=['total_amount', 'grand_total']
    )
    
    return order.grand_total

# advance the next delivery date for customer subscription based on the billing frequency



def advance_subscription_delivery(subscription):
    if subscription.status != "active":
        return

    if not subscription.next_delivery_date:
        return

    if subscription.bundle.billing_frequency == "monthly":
        subscription.next_delivery_date += relativedelta(months=1)

    elif subscription.bundle.billing_frequency == "yearly":
        subscription.next_delivery_date += relativedelta(years=1)

    subscription.save(update_fields=["next_delivery_date"])