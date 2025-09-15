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
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)
        self.company = company

        # Filter tax rates by company
        if company:
            self.fields["tax_rate"].queryset = TaxRate.objects.filter(
                company=company, is_active=True
            ).order_by("name")

        # Make tax rate optional
        self.fields["tax_rate"].empty_label = "No tax rate"

    def clean_code(self):
        """Validate that account code is unique within the company."""
        code = self.cleaned_data.get('code')
        if code and self.company:
            # Check if account with this code already exists for this company
            # Exclude the current instance if we're editing an existing account
            existing_accounts = Account.objects.filter(
                company=self.company, 
                code=code
            )
            
            # If we're editing an existing account, exclude it from the check
            if self.instance and self.instance.pk:
                existing_accounts = existing_accounts.exclude(pk=self.instance.pk)
            
            if existing_accounts.exists():
                existing = existing_accounts.first()
                raise forms.ValidationError(
                    f'Account code "{code}" already exists for "{existing.name}". '
                    f'Please use a different code (e.g., {self._suggest_next_code(code)}).'
                )
        return code

    def _suggest_next_code(self, base_code):
        """Suggest the next available code based on the attempted code."""
        try:
            base_num = int(base_code)
            # Try incrementing the code
            for i in range(1, 10):
                suggested_code = str(base_num + i)
                query = Account.objects.filter(
                    company=self.company, 
                    code=suggested_code
                )
                # Exclude current instance if editing
                if self.instance and self.instance.pk:
                    query = query.exclude(pk=self.instance.pk)
                
                if not query.exists():
                    return suggested_code
        except ValueError:
            # If code is not numeric, suggest adding a suffix
            for suffix in ['A', 'B', 'C']:
                suggested_code = f"{base_code}{suffix}"
                query = Account.objects.filter(
                    company=self.company, 
                    code=suggested_code
                )
                # Exclude current instance if editing
                if self.instance and self.instance.pk:
                    query = query.exclude(pk=self.instance.pk)
                
                if not query.exists():
                    return suggested_code
        return f"{base_code}_NEW"
        return f"{base_code}_NEW"
