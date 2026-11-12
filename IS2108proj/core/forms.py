from django import forms

from .models import Review, SubscriptionBundleReview


class CheckoutForm(forms.Form):
    delivery_address = forms.CharField(
        label="Delivery Address",
        strip=True,
        widget=forms.Textarea(
            attrs={
                "class": "field-control",
                "rows": 3,
                "placeholder": "Enter your delivery address",
                "aria-describedby": "delivery-address-error",
            }
        ),
    )


class SubscriptionEnrollmentForm(forms.Form):
    delivery_address = forms.CharField(
        label="Delivery Address",
        strip=True,
        widget=forms.Textarea(
            attrs={
                "class": "field-control",
                "rows": 3,
                "placeholder": "Enter your delivery address",
            }
        ),
    )


class CustomerReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect(),
            "comment": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "rating": "Your rating",
            "comment": "Your review",
        }


class SubscriptionBundleReviewForm(forms.ModelForm):
    class Meta:
        model = SubscriptionBundleReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect(),
            "comment": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "rating": "Your rating",
            "comment": "Your review",
        }
