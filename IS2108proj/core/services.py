from decimal import Decimal

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