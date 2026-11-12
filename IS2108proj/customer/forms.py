from django import forms
from django.contrib.auth.models import User
from core.models import Category, CustomerProfile, QuestionnaireResponse

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
    preferred_category = forms.ChoiceField(
        choices=Category.CATEGORY_CHOICES,
        label="Which coffee format do you prefer?",
        help_text="Choose whole bean, ground coffee, instant, or drip bags.",
        widget=forms.RadioSelect(),
    )

    class Meta:
        model = QuestionnaireResponse
        fields = [
            "preferred_flavour",
            "preferred_brewing_method",
            "preferred_caffeine_type",
        ]
        labels = {
            "preferred_flavour": "Which flavor notes sound best to you?",
            "preferred_brewing_method": "How do you usually brew your coffee?",
            "preferred_caffeine_type": "How much caffeine would you like?",
        }
        widgets = {
            "preferred_flavour": forms.RadioSelect(),
            "preferred_brewing_method": forms.RadioSelect(),
            "preferred_caffeine_type": forms.RadioSelect(),
        }
        help_texts = {
            "preferred_flavour": "Pick the flavor profile you are most drawn to.",
            "preferred_brewing_method": "Choose the brewing method you use most often.",
            "preferred_caffeine_type": "Choose regular coffee or a decaf option.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_category"].required = True
        if self.instance and self.instance.preferred_category_id:
            self.initial["preferred_category"] = self.instance.preferred_category.name
        self.order_fields(
            [
                "preferred_category",
                "preferred_flavour",
                "preferred_brewing_method",
                "preferred_caffeine_type",
            ]
        )
        for field_name in ("preferred_flavour",):
            model_field = QuestionnaireResponse._meta.get_field(field_name)
            self.fields[field_name].choices = model_field.choices

        self.fields["preferred_brewing_method"].choices = [
            ("espresso", "Espresso / Moka"),
            ("french_press", "French Press"),
            ("pour_over", "Pour-over / V60"),
            ("filter", "Drip / Filter"),
        ]
        self.fields["preferred_caffeine_type"].choices = [
            ("caffeinated", "Regular (caffeinated)"),
            ("decaf", "Decaf"),
        ]