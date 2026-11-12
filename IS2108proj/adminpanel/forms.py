from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from core.models import Product, SubscriptionBundle, BundleItem, Order, Review
from core.currency import RATES as CURRENCY_RATES, normalize_currency
from django.contrib.auth import authenticate


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.currency = normalize_currency(kwargs.pop("currency", "SGD"))

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            original_sgd_price = self.instance.price

            converted_price = (
                original_sgd_price
                * CURRENCY_RATES[self.currency]
            )

            self.initial["price"] = f"{converted_price:.2f}"

    def clean_price(self):
        price = self.cleaned_data.get("price")

        if price is None:
            return price

        price = Decimal(str(price))

        # Already in SGD
        if self.currency == "SGD":
            return price.quantize(Decimal("0.01"))

        # Convert entered USD/EUR value back into SGD
        sgd_price = price / CURRENCY_RATES[self.currency]

        return sgd_price.quantize(Decimal("0.01"))


class InventoryForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["stock_level", "reorder_threshold", "is_visible"]

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["delivery_status"]

    def clean_delivery_status(self):
        delivery_status = self.cleaned_data["delivery_status"]
        if self.instance.delivery_status == "cancelled" and delivery_status != "cancelled":
            raise forms.ValidationError("Cancelled orders cannot be reopened.")
        if (
            self.instance.delivery_status in {"shipped", "delivered"}
            and delivery_status == "cancelled"
        ):
            raise forms.ValidationError(
                "Shipped or delivered orders cannot be cancelled. Handle them through a return process."
            )
        return delivery_status

class SubscriptionBundleForm(forms.ModelForm):
    class Meta:
        model = SubscriptionBundle
        fields = [
            "name",
            "billing_frequency",
            "price_per_delivery",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        self.currency = normalize_currency(kwargs.pop("currency", "SGD"))
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            converted = self.instance.price_per_delivery * CURRENCY_RATES[self.currency]
            self.initial["price_per_delivery"] = f"{converted:.2f}"

    def clean_price_per_delivery(self):
        price = self.cleaned_data.get("price_per_delivery")
        if price is None:
            return price

        price = Decimal(str(price))

        if self.currency == "SGD":
            return price.quantize(Decimal("0.01"))

        return (price / CURRENCY_RATES[self.currency]).quantize(Decimal("0.01"))

    def save(self, commit=True):
        bundle = super().save(commit=False)
        bundle.price_per_delivery = self.cleaned_data["price_per_delivery"]

        if commit:
            bundle.save()

        return bundle

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
    extra =0,
    can_delete=True
)


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["is_visible"]

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password:
            user = authenticate(username=username, password=password)

            if user is None:
                raise forms.ValidationError("Invalid username or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            if not user.is_staff:
                raise forms.ValidationError("This account is not an admin account.")

            cleaned_data["user"] = user

        return cleaned_data