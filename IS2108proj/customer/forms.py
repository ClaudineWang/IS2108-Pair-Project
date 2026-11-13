import re

from django import forms
from django.contrib.auth.models import User
from core.models import Category, QuestionnaireResponse

PHONE_REGION_CHOICES = [
    ("SG", "Singapore (+65)"),
    ("US", "United States (+1)"),
    ("AT", "Austria (+43)"),
    ("BE", "Belgium (+32)"),
    ("CY", "Cyprus (+357)"),
    ("EE", "Estonia (+372)"),
    ("FI", "Finland (+358)"),
    ("FR", "France (+33)"),
    ("DE", "Germany (+49)"),
    ("GR", "Greece (+30)"),
    ("IE", "Ireland (+353)"),
    ("IT", "Italy (+39)"),
    ("LV", "Latvia (+371)"),
    ("LT", "Lithuania (+370)"),
    ("LU", "Luxembourg (+352)"),
    ("MT", "Malta (+356)"),
    ("NL", "Netherlands (+31)"),
    ("PT", "Portugal (+351)"),
    ("SK", "Slovakia (+421)"),
    ("SI", "Slovenia (+386)"),
    ("ES", "Spain (+34)"),
]

PHONE_REGION_CODES = {
    region: label.rsplit("(+", 1)[1].rstrip(")")
    for region, label in PHONE_REGION_CHOICES
}


def phone_region_for_value(value):
    compact_value = re.sub(r"[\s().-]+", "", str(value or "")).strip()
    if compact_value.startswith("00"):
        compact_value = "+" + compact_value[2:]

    if compact_value.startswith("+"):
        digits = compact_value[1:]
        for region, code in sorted(
            PHONE_REGION_CODES.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        ):
            if digits.startswith(code):
                return region

    return "SG"


def phone_without_region_code(value, region):
    raw_value = str(value or "").strip()
    code = PHONE_REGION_CODES[region]
    prefix_pattern = rf"^\s*(?:\+{re.escape(code)}|00{re.escape(code)})[\s().-]*"
    return re.sub(prefix_pattern, "", raw_value, count=1)

class CustomerSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username"]

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

        return user


class CustomerOnboardingForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")
    phone_region = forms.ChoiceField(
        choices=PHONE_REGION_CHOICES,
        label="Country or region",
    )
    phone_number = forms.CharField(
        max_length=20,
        label="Phone number",
        help_text="Choose a country or region above, then enter the local phone number.",
    )
    delivery_address = forms.CharField(
        label="Delivery address",
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def clean_first_name(self):
        value = self.cleaned_data["first_name"].strip()
        if not value:
            raise forms.ValidationError("Enter your first name.")
        return value

    def clean_last_name(self):
        value = self.cleaned_data["last_name"].strip()
        if not value:
            raise forms.ValidationError("Enter your last name.")
        return value

    def clean_phone_number(self):
        value = self.cleaned_data["phone_number"].strip()
        if not value:
            raise forms.ValidationError("Enter your phone number.")
        region = self.cleaned_data.get("phone_region", "SG")
        value = phone_without_region_code(value, region)
        return f"+{PHONE_REGION_CODES[region]} {value}"

    def clean_delivery_address(self):
        value = self.cleaned_data["delivery_address"].strip()
        if not value:
            raise forms.ValidationError("Enter your delivery address.")
        return value

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
            "preferred_roast",
            "preferred_flavour",
            "preferred_brewing_method",
            "preferred_caffeine_type",
        ]
        labels = {
            "preferred_roast": "Which roast level do you prefer?",
            "preferred_flavour": "Which flavor notes sound best to you?",
            "preferred_brewing_method": "How do you usually brew your coffee?",
            "preferred_caffeine_type": "How much caffeine would you like?",
        }
        widgets = {
            "preferred_roast": forms.RadioSelect(),
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
        for field_name in ("preferred_roast", "preferred_flavour"):
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
