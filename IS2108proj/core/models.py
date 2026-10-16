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
    def stock_status(self):
        if self.stock_level == 0:
            return "Out of Stock"
        elif self.stock_level <= self.reorder_threshold:
            return "Low in Stock"
        else:
            return "In Stock"
    def __str__(self):
        return self.name

