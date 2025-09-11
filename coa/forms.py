# COA forms.py - Tax Rate forms with proper widgets
from django import forms
from .models import TaxRate, Account


class TaxRateForm(forms.ModelForm):
    """Tax Rate form with proper widgets and validation."""

    class Meta:
        model = TaxRate
        fields = [
            "name",
            "rate",
            "description",
            "tax_authority",
            "tax_type",
            "is_default",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., VAT 10%",
                    "maxlength": 100,
                }
            ),
            "rate": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional description...",
                }
            ),
            "tax_authority": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g., IRS, HMRC, etc."}
            ),
            "tax_type": forms.Select(attrs={"class": "form-select"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Convert rate from decimal to percentage for display
        if self.instance and self.instance.pk:
            self.initial["rate"] = self.instance.rate * 100

    def clean_rate(self):
        """Convert percentage back to decimal."""
        rate = self.cleaned_data.get("rate")
        if rate is not None:
            # Convert percentage to decimal
            return rate / 100
        return rate

    def clean_name(self):
        """Validate tax rate name uniqueness per company."""
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            # Company will be set in the view
            if hasattr(self.instance, "company") and self.instance.company:
                existing = TaxRate.objects.filter(
                    company=self.instance.company, name__iexact=name
                ).exclude(pk=self.instance.pk)
                if existing.exists():
                    raise forms.ValidationError(
                        f'A tax rate with the name "{name}" already exists for this company.'
                    )
        return name


class TaxRateEditForm(TaxRateForm):
    """Extended form for editing tax rates."""

    class Meta(TaxRateForm.Meta):
        fields = TaxRateForm.Meta.fields + ["is_active"]
        widgets = TaxRateForm.Meta.widgets.copy()
        widgets.update(
            {"is_active": forms.CheckboxInput(attrs={"class": "form-check-input"})}
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If this is a system-defined tax rate, restrict certain fields
        if self.instance and self.instance.is_system_defined:
            # System defined rates can only change status and description
            self.fields["name"].widget.attrs["readonly"] = True
            self.fields["rate"].widget.attrs["readonly"] = True
            self.fields["tax_type"].widget.attrs["disabled"] = True

            # Add helpful text
            self.fields["name"].help_text = (
                "System defined tax rate names cannot be changed"
            )
            self.fields["rate"].help_text = (
                "System defined tax rate values cannot be changed"
            )

    def clean_name(self):
        """Prevent changing name of system-defined tax rates."""
        name = self.cleaned_data.get("name")
        if self.instance and self.instance.is_system_defined and self.instance.pk:
            if name != self.instance.name:
                raise forms.ValidationError(
                    "You cannot change the name of system defined tax rates."
                )
        return super().clean_name()

    def clean_rate(self):
        """Prevent changing rate of system-defined tax rates."""
        rate = self.cleaned_data.get("rate")
        if self.instance and self.instance.is_system_defined and self.instance.pk:
            # Convert current rate to percentage for comparison
            current_rate = self.instance.rate * 100
            if abs(rate - current_rate) > 0.001:  # Allow for floating point precision
                raise forms.ValidationError(
                    "You cannot change the rate of system defined tax rates."
                )
        return super().clean_rate()


class AccountForm(forms.ModelForm):
    """Account form with proper widgets."""

    class Meta:
        model = Account
        fields = [
            "code",
            "name",
            "account_type",
            "tax_rate",
            "description",
            "parent_account",
        ]

        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 1000",
                    "maxlength": 10,
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account name",
                    "maxlength": 150,
                }
            ),
            "account_type": forms.Select(attrs={"class": "form-select"}),
            "tax_rate": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional description...",
                }
            ),
            "parent_account": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        # Filter tax rates and parent accounts by company
        if company:
            self.fields["tax_rate"].queryset = TaxRate.objects.filter(
                company=company, is_active=True
            ).order_by("name")
            self.fields["parent_account"].queryset = Account.objects.filter(
                company=company, is_active=True
            ).order_by("code")

        # Make tax rate optional
        self.fields["tax_rate"].empty_label = "No tax rate"
        self.fields["parent_account"].empty_label = "No parent account"
