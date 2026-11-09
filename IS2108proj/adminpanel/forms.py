from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.db.models import Q
from core.models import Product, Order, OrderItem, SubscriptionBundle, BundleItem, Review

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["stock_level", "reorder_threshold", "is_visible"]

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["delivery_status", "delivery_address"]

class SubscriptionBundleForm(forms.ModelForm):
    class Meta:
        model = SubscriptionBundle
        fields = ["name", "description", "price_per_delivery", "billing_frequency", "is_active"]

class BundleItemForm(forms.ModelForm):
    class Meta:
        model = BundleItem
        fields = ["product", "quantity"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args, **kwargs):
        bundle = kwargs.pop("bundle", None)
        super().__init__(*args, **kwargs)

        used_product_ids = []

        if bundle is not None:
            used_product_ids = list(
                BundleItem.objects.filter(subscription_bundle=bundle)
                .exclude(pk=self.instance.pk)
                .values_list("product_id", flat=True)
            )

        available_products = Product.objects.exclude(id__in=used_product_ids)

        if self.instance and self.instance.pk:
            available_products = available_products | Product.objects.filter(id=self.instance.product_id)

        self.fields["product"].queryset = available_products.distinct()

class BaseBundleItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.bundle = kwargs.pop("bundle", None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["bundle"] = self.bundle
        return super()._construct_form(i, **kwargs)

BundleItemFormSet = inlineformset_factory(
    SubscriptionBundle,
    BundleItem,
    form=BundleItemForm,
    formset=BaseBundleItemFormSet,
    extra=1,
    can_delete=True
)

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["is_visible"]

