from email.mime import image

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone_number = models.CharField(max_length=20, blank=True)
    delivery_address = models.TextField(blank=True)
    delivery_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.username

class Category(models.Model):
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    CAFFEINE_TYPE = [
        ('caffeinated', 'Caffeinated'),
        ('decaf', 'Decaf'),
    ]
    ROAST_LEVEL = [ ('light', 'Light'),
                    ('medium', 'Medium'),
                    ('dark', 'Dark'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    tasting_notes = models.TextField(blank=True)
    caffeine_type = models.CharField(max_length=20, choices=CAFFEINE_TYPE)
    roast_level = models.CharField(max_length=20, choices=ROAST_LEVEL)
    origin_country = models.CharField(max_length=100, blank=True)
    stock_level = models.PositiveIntegerField(default=0)
    reorder_threshold = models.PositiveIntegerField(default=10 )
    is_visible = models.BooleanField(default=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def stock_status(self):
        if self.stock_level == 0:
            return "Out of Stock"
        elif self.stock_level <= self.reorder_threshold:
            return "Low in Stock"
        else:
            return "In Stock"
    def __str__(self):
        return self.name

class Order(models.Model):
    ORDER_TYPE = [
        ('one-time', 'One-Time'),
        ('subscription', 'Subscription')
    ]
    DELIVERY_STATUS = [
        ('pending', 'Pending'),
        ('roasting', 'Roasting'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    customer = models.ForeignKey(CustomerProfile, on_delete=models.PROTECT, related_name='orders')
    #subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_address = models.TextField()
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    def __str__(self):
        return f"Order {self.id}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def subtotal(self):
        return self.quantity * self.price_at_purchase
    
    def __str__(self):
        return f" {self.product.name} in Order {self.order.id}"

class SubscriptionBundle(models.Model):
    BILLING_FREQUENCY = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ]
    name = models.CharField(max_length=100)
    description= models.TextField(blank=True)
    price_per_delivery= models.DecimalField(max_digits=10, decimal_places=2)
    billing_frequency = models.CharField(max_length=20, choices=BILLING_FREQUENCY, default='monthly')
    is_active = models.BooleanField(default=False)
    products = models.ManyToManyField(Product, through= 'BundleItem', related_name ='subscription_bundles')
    
    @property
    def total_items(self):
        return sum(
            item.quantity
            for item in self.bundle_items.all()
        )
    
    def __str__(self):
        return self.name
    
class BundleItem(models.Model):
    subscription_bundle = models.ForeignKey(SubscriptionBundle, on_delete=models.CASCADE, related_name ='bundle_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name ='bundle_items')
    quantity= models.PositiveIntegerField(default=1)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subscription_bundle", "product"],
                name="unique_product_per_bundle"
        )
    ]
    def __str__(self):
        return f"{self.product.name} in {self.subscription_bundle.name}"
    
