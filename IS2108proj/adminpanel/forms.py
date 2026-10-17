from django import forms
from django.forms import inlineformset_factory
from core.models import Product, Order, OrderItem, SubscriptionBundle, BundleItem

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'origin_country', 'roast_level', 'caffeine_type', 'tasting_notes', 'price', 'origin_country', 'stock_level', 'image', 'is_visible']

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [ 'stock_level', 'reorder_threshold']
        labels = {
            "stock_level" : "New Stock Quantity",
            "reorder_theshold": "Low Stock Warning"
        }

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['delivery_status']

class SubscriptionBundleForm(forms.ModelForm):
    class Meta:
        model = SubscriptionBundle
        fields = ['name', 'description', 'price_per_delivery', 'billing_frequency', 'is_active']
class BundleItemForm(forms.ModelForm):
    class Meta:
        model = BundleItem
        fields= ['product', 'quantity']
BundleItemFormSet = inlineformset_factory(
    SubscriptionBundle,
    BundleItem,
    form=BundleItemForm,
    extra=1,
    can_delete=True
)