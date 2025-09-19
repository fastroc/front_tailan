"""
Forms for payment processing functionality
"""
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Payment, PaymentAllocation, AutoPayment
from loans_core.models import Loan
from loans_schedule.models import ScheduledPayment


class PaymentForm(forms.ModelForm):
    """Form for recording loan payments"""
    
    class Meta:
        model = Payment
        fields = [
            'loan', 'amount', 'payment_date', 'payment_method', 'reference_number',
            'notes', 'is_verified'
        ]
        widgets = {
            'loan': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Transaction reference, check number, etc.'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about this payment'
            }),
            'is_verified': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            # Filter loans to only show active loans from the user's company
            self.fields['loan'].queryset = Loan.objects.filter(
                company=company, status='active'
            ).select_related('customer', 'loan_product')
        
        # Set default payment date to today
        if not self.instance.pk:
            self.fields['payment_date'].initial = timezone.now().date()
            self.fields['is_verified'].initial = True
    
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError('Payment amount must be greater than zero.')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        loan = cleaned_data.get('loan')
        amount = cleaned_data.get('amount')
        
        if loan and amount:
            # Check if payment exceeds outstanding balance
            if amount > loan.current_balance:
                # Allow overpayment but warn user
                self.add_error('amount', 
                    f'Payment amount (${amount}) exceeds loan balance (${loan.current_balance}). '
                    f'This will result in an overpayment credit.'
                )
        
        return cleaned_data


class QuickPaymentForm(forms.ModelForm):
    """Quick payment form for common scenarios"""
    
    pay_full_amount = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Pay Full Outstanding Balance'
    )
    
    apply_to_overdue = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Apply to Overdue Payments First',
        initial=True
    )
    
    class Meta:
        model = Payment
        fields = ['loan', 'amount', 'payment_method', 'reference_number']
        widgets = {
            'loan': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reference number (optional)'
            })
        }
    
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['loan'].queryset = Loan.objects.filter(
                company=company, status='active'
            ).select_related('customer')
    
    def clean(self):
        cleaned_data = super().clean()
        loan = cleaned_data.get('loan')
        pay_full_amount = cleaned_data.get('pay_full_amount')
        
        if loan and pay_full_amount:
            cleaned_data['amount'] = loan.current_balance
            cleaned_data['payment_date'] = timezone.now().date()
        
        return cleaned_data


class PaymentAllocationForm(forms.ModelForm):
    """Form for manual payment allocation"""
    
    class Meta:
        model = PaymentAllocation
        fields = [
            'scheduled_payment', 'principal_amount', 'interest_amount',
            'fee_amount', 'penalty_amount', 'notes'
        ]
        widgets = {
            'scheduled_payment': forms.Select(attrs={
                'class': 'form-select',
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
            'fee_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.00',
                'value': '0.00'
            }),
            'penalty_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.00',
                'value': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional allocation notes'
            })
        }
    
    def __init__(self, *args, payment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if payment:
            # Filter scheduled payments to only show unpaid payments for this loan
            self.fields['scheduled_payment'].queryset = ScheduledPayment.objects.filter(
                schedule__loan=payment.loan, is_paid=False
            ).order_by('due_date')
    
    def clean(self):
        cleaned_data = super().clean()
        principal = cleaned_data.get('principal_amount', Decimal('0'))
        interest = cleaned_data.get('interest_amount', Decimal('0'))
        fee = cleaned_data.get('fee_amount', Decimal('0'))
        penalty = cleaned_data.get('penalty_amount', Decimal('0'))
        
        total_allocation = principal + interest + fee + penalty
        if total_allocation <= 0:
            raise ValidationError('Total allocation amount must be greater than zero.')
        
        return cleaned_data


class AutoPaymentForm(forms.ModelForm):
    """Form for setting up automatic payments"""
    
    class Meta:
        model = AutoPayment
        fields = [
            'loan', 'payment_amount', 'payment_frequency', 'start_date',
            'end_date', 'payment_method', 'bank_account_info', 'is_active', 'notes'
        ]
        widgets = {
            'loan': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'payment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'payment_frequency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'bank_account_info': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Bank account details for automatic payments'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about this auto-payment setup'
            })
        }
    
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['loan'].queryset = Loan.objects.filter(
                company=company, status='active'
            ).select_related('customer')
        
        # Set default dates
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()
            self.fields['is_active'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError('End date must be after start date.')
        
        return cleaned_data


class PaymentSearchForm(forms.Form):
    """Form for searching payments"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('verified', 'Verified'),
        ('pending', 'Pending Verification'),
        ('failed', 'Failed'),
    ]
    
    PERIOD_CHOICES = [
        ('', 'All Time'),
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('custom', 'Custom Range'),
    ]
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by reference number, customer name, or loan number'
        }),
        label='Search'
    )
    
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Loan'
    )
    
    payment_method = forms.ChoiceField(
        choices=[('', 'All Methods')] + Payment.PAYMENT_METHOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Payment Method'
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Status'
    )
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Period'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='From Date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='To Date'
    )
    
    min_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.00'
        }),
        label='Min Amount'
    )
    
    max_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.00'
        }),
        label='Max Amount'
    )
    
    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['loan'].queryset = Loan.objects.filter(
                company=company
            ).select_related('customer')
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        
        if date_from and date_to and date_to < date_from:
            raise ValidationError('End date must be after start date.')
        
        if min_amount and max_amount and max_amount < min_amount:
            raise ValidationError('Maximum amount must be greater than minimum amount.')
        
        return cleaned_data


class PaymentReversalForm(forms.Form):
    """Form for reversing payments"""
    
    REVERSAL_REASON_CHOICES = [
        ('error', 'Payment Error'),
        ('duplicate', 'Duplicate Payment'),
        ('insufficient_funds', 'Insufficient Funds'),
        ('customer_request', 'Customer Request'),
        ('bank_error', 'Bank Error'),
        ('other', 'Other'),
    ]
    
    reversal_reason = forms.ChoiceField(
        choices=REVERSAL_REASON_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Reversal Reason'
    )
    
    reversal_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Explain the reason for this payment reversal',
            'required': True
        }),
        label='Reversal Notes'
    )
    
    reverse_allocations = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Reverse All Payment Allocations'
    )
    
    notify_customer = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Notify Customer of Reversal'
    )
    
    def clean_reversal_notes(self):
        notes = self.cleaned_data['reversal_notes']
        if len(notes.strip()) < 10:
            raise ValidationError('Please provide a detailed explanation for the reversal.')
        return notes


class BulkPaymentProcessForm(forms.Form):
    """Form for bulk payment processing"""
    
    PROCESS_TYPE_CHOICES = [
        ('verify', 'Verify Payments'),
        ('allocate', 'Auto-Allocate Payments'),
        ('reverse', 'Reverse Payments'),
        ('export', 'Export Payment Data'),
    ]
    
    payment_ids = forms.CharField(
        widget=forms.HiddenInput(),
        label='Selected Payments'
    )
    
    process_type = forms.ChoiceField(
        choices=PROCESS_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Process Type'
    )
    
    allocation_priority = forms.ChoiceField(
        choices=[
            ('overdue_first', 'Overdue Payments First'),
            ('oldest_first', 'Oldest Payments First'),
            ('principal_first', 'Principal First'),
            ('interest_first', 'Interest First'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Allocation Priority'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about this bulk process'
        }),
        label='Process Notes'
    )
    
    def clean_payment_ids(self):
        payment_ids = self.cleaned_data['payment_ids']
        if not payment_ids:
            raise ValidationError('No payments selected for processing.')
        
        try:
            ids = [int(id.strip()) for id in payment_ids.split(',') if id.strip()]
            if not ids:
                raise ValidationError('No valid payment IDs provided.')
            return ids
        except ValueError:
            raise ValidationError('Invalid payment ID format.')
    
    def clean(self):
        cleaned_data = super().clean()
        process_type = cleaned_data.get('process_type')
        allocation_priority = cleaned_data.get('allocation_priority')
        
        if process_type == 'allocate' and not allocation_priority:
            raise ValidationError('Allocation priority is required for auto-allocation.')
        
        return cleaned_data
