from decimal import Decimal
from dateutil.relativedelta import relativedelta

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