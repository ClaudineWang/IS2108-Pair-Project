from django import forms
from django.contrib.auth.models import User
from core.models import CustomerProfile, QuestionnaireResponse, Category

class CustomerSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    phone_number = forms.CharField(max_length=20, required=True)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        CustomerProfile.objects.update_or_create(
            user=user,
            defaults={
                "phone_number": self.cleaned_data["phone_number"],
            }
        )

        return user

class QuestionnaireResponseForm(forms.ModelForm):
    class Meta:
        model = QuestionnaireResponse
        fields = ["preferred_roast", "preferred_flavour", "preferred_brewing_method", "preferred_caffeine_type", "preferred_category"]
        labels = {
            "preferred_roast": "What Roast Level Do You Prefer?",
            "preferred_flavour": "What Flavour Profile Do You Prefer?",
            "preferred_brewing_method": "How Do You Usually Brew Your Coffee?",
            "preferred_caffeine_type": "Do You Prefer Caffeinated or Decaf Coffee?",
            "preferred_category": "What Type of Coffee Do You Prefer?",
        }
        widgets = {
            "preferred_roast": forms.Select(),
            "preferred_flavour": forms.Select(),
            "preferred_brewing_method": forms.Select(),
            "preferred_caffeine_type": forms.Select(),
            "preferred_category": forms.Select(),
        }
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['preferred_category'].queryset = Category.objects.all().order_by('name')