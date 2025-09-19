"""
Forms for payment scheduling functionality
"""
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import PaymentSchedule, ScheduledPayment, CustomPaymentPreset, PaymentDateRule
from loans_core.models import Loan


class PaymentScheduleForm(forms.ModelForm):
    """Form for creating payment schedules"""
    
    class Meta:
        model = PaymentSchedule
        fields = [
            'loan', 'schedule_type', 'payment_frequency', 'total_payments',
            'total_principal', 'total_interest', 'total_amount',
            'grace_period_months', 'balloon_payment_amount', 'status'
        ]
        widgets = {
            'loan': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'schedule_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'payment_frequency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'total_payments': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '360',
                'required': True
            }),
            'total_principal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'total_interest': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.00',
                'required': True
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'grace_period_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '12',
                'value': '0'
            }),
            'balloon_payment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.00'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            # Filter loans to only show loans from the user's company
            self.fields['loan'].queryset = Loan.objects.filter(
                company=company, status__in=['approved', 'active']
            ).select_related('customer', 'loan_product')
        
        # Set default status to active
        if not self.instance.pk:
            self.fields['status'].initial = 'active'
    
    def clean(self):
        cleaned_data = super().clean()
        total_principal = cleaned_data.get('total_principal')
        total_interest = cleaned_data.get('total_interest')
        total_amount = cleaned_data.get('total_amount')
        
        if total_principal and total_interest and total_amount:
            calculated_total = total_principal + total_interest
            if abs(calculated_total - total_amount) > Decimal('0.01'):
                cleaned_data['total_amount'] = calculated_total
        
        return cleaned_data


class ScheduledPaymentForm(forms.ModelForm):
    """Form for individual scheduled payments"""
    
    class Meta:
        model = ScheduledPayment
        fields = [
            'due_date', 'principal_amount', 'interest_amount',
            'total_amount', 'status'
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'principal_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.00',
                'required': True
            }),
            'interest_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.00',
                'required': True
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True,
                'readonly': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        principal = cleaned_data.get('principal_amount', Decimal('0'))
        interest = cleaned_data.get('interest_amount', Decimal('0'))
        total = cleaned_data.get('total_amount', Decimal('0'))
        
        calculated_total = principal + interest
        if abs(calculated_total - total) > Decimal('0.01'):
            cleaned_data['total_amount'] = calculated_total
        
        return cleaned_data


class CustomPaymentPresetForm(forms.ModelForm):
    """Form for creating custom payment presets"""
    
    class Meta:
        model = CustomPaymentPreset
        fields = [
            'name', 'description', 'preset_type', 'default_frequency',
            'grace_period_months', 'has_balloon_payment', 'balloon_percentage',
            'payment_pattern', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Bi-weekly Salary Schedule',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe when and how this preset should be used'
            }),
            'preset_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'default_frequency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'grace_period_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '12',
                'value': '0'
            }),
            'has_balloon_payment': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'balloon_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.00',
                'max': '100.00'
            }),
            'payment_pattern': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'JSON pattern for custom schedules (optional)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['is_active'].initial = True


class PaymentDateRuleForm(forms.ModelForm):
    """Form for payment date rules"""
    
    class Meta:
        model = PaymentDateRule
        fields = [
            'rule_name', 'rule_type', 'day_of_month', 'weekday',
            'custom_dates', 'skip_weekends', 'skip_holidays', 'is_active'
        ]
        widgets = {
            'rule_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Last Friday of Month',
                'required': True
            }),
            'rule_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'day_of_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '31'
            }),
            'weekday': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '6'
            }),
            'custom_dates': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'JSON array of custom dates'
            }),
            'skip_weekends': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'skip_holidays': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['is_active'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        rule_type = cleaned_data.get('rule_type')
        day_of_month = cleaned_data.get('day_of_month')
        weekday = cleaned_data.get('weekday')
        
        # Validate based on rule type
        if rule_type == 'monthly_same_day':
            if not day_of_month:
                raise ValidationError('Day of month is required for monthly same day rules.')
            if day_of_month > 28:
                self.add_error('day_of_month', 
                    'Day of month should be 28 or less to ensure it exists in all months.')
        
        elif rule_type in ['weekly_same_weekday', 'bi_weekly_from_start']:
            if weekday is None:
                raise ValidationError('Weekday is required for weekly rules.')
        
        return cleaned_data


class PaymentScheduleGeneratorForm(forms.Form):
    """Form for generating payment schedules with advanced options"""
    
    CALCULATION_METHOD_CHOICES = [
        ('equal_payment', 'Equal Monthly Payment'),
        ('equal_principal', 'Equal Principal Payment'),
        ('interest_only', 'Interest Only with Balloon'),
        ('custom', 'Custom Schedule'),
    ]
    
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Loan'
    )
    
    calculation_method = forms.ChoiceField(
        choices=CALCULATION_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        initial='equal_payment',
        label='Calculation Method'
    )
    
    payment_frequency = forms.ChoiceField(
        choices=PaymentSchedule.FREQUENCY,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        initial='monthly',
        label='Payment Frequency'
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        }),
        label='First Payment Date'
    )
    
    custom_payment_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Custom Payment Amount'
    )
    
    balloon_payment = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.00'
        }),
        label='Balloon Payment Amount'
    )
    
    grace_period_days = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '30',
            'value': '5'
        }),
        label='Grace Period (Days)'
    )
    
    apply_payment_rule = forms.ModelChoiceField(
        queryset=PaymentDateRule.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Payment Date Rule'
    )
    
    generate_late_fees = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Generate Late Fee Schedule'
    )
    
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['loan'].queryset = Loan.objects.filter(
                company=company, status__in=['approved', 'active']
            ).select_related('customer', 'loan_product')
            
            self.fields['apply_payment_rule'].queryset = PaymentDateRule.objects.filter(
                company=company, is_active=True
            )
        
        # Set default start date
        self.fields['start_date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        calculation_method = cleaned_data.get('calculation_method')
        custom_payment_amount = cleaned_data.get('custom_payment_amount')
        loan = cleaned_data.get('loan')
        
        if calculation_method == 'custom' and not custom_payment_amount:
            raise ValidationError('Custom payment amount is required for custom schedules.')
        
        if loan and custom_payment_amount:
            # Basic validation that payment covers at least interest
            monthly_interest = loan.current_balance * (loan.interest_rate / 100 / 12)
            if custom_payment_amount < monthly_interest:
                self.add_error('custom_payment_amount',
                    f'Payment amount should be at least ${monthly_interest:.2f} '
                    f'to cover monthly interest.')
        
        return cleaned_data


class BulkPaymentUpdateForm(forms.Form):
    """Form for bulk updating scheduled payments"""
    
    UPDATE_TYPE_CHOICES = [
        ('adjust_amount', 'Adjust Payment Amounts'),
        ('reschedule_dates', 'Reschedule Payment Dates'),
        ('mark_paid', 'Mark as Paid'),
        ('mark_unpaid', 'Mark as Unpaid'),
        ('add_late_fees', 'Add Late Fees'),
    ]
    
    payment_ids = forms.CharField(
        widget=forms.HiddenInput(),
        label='Selected Payments'
    )
    
    update_type = forms.ChoiceField(
        choices=UPDATE_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Update Type'
    )
    
    adjustment_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        }),
        label='Adjustment Amount'
    )
    
    adjustment_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '-100',
            'max': '100'
        }),
        label='Adjustment Percentage'
    )
    
    date_offset_days = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '-365',
            'max': '365'
        }),
        label='Date Offset (Days)'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about this bulk update'
        }),
        label='Update Notes'
    )
    
    def clean_payment_ids(self):
        payment_ids = self.cleaned_data['payment_ids']
        if not payment_ids:
            raise ValidationError('No payments selected for update.')
        
        try:
            ids = [int(id.strip()) for id in payment_ids.split(',') if id.strip()]
            if not ids:
                raise ValidationError('No valid payment IDs provided.')
            return ids
        except ValueError:
            raise ValidationError('Invalid payment ID format.')
    
    def clean(self):
        cleaned_data = super().clean()
        update_type = cleaned_data.get('update_type')
        adjustment_amount = cleaned_data.get('adjustment_amount')
        adjustment_percentage = cleaned_data.get('adjustment_percentage')
        date_offset_days = cleaned_data.get('date_offset_days')
        
        if update_type == 'adjust_amount':
            if not adjustment_amount and not adjustment_percentage:
                raise ValidationError(
                    'Either adjustment amount or percentage is required for amount adjustments.'
                )
        
        elif update_type == 'reschedule_dates':
            if date_offset_days is None:
                raise ValidationError('Date offset is required for rescheduling.')
        
        return cleaned_data
