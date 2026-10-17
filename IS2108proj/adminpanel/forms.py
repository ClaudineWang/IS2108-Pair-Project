from django import forms
from core.models import Product

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
        