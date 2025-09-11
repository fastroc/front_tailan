from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class SimpleRegistrationForm(UserCreationForm):
    """Super simple registration - just the basics!"""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name',
            'id': 'firstName'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Last Name',
            'id': 'lastName'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields Bootstrap-ready
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # Friendly placeholders
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Choose a username',
            'id': 'username'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Create password',
            'id': 'password1'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm password',
            'id': 'password2'
        })
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters long.')
        return username


class SimpleProfileForm(forms.ModelForm):
    """Simple profile editing form."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'firstName'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'lastName'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'username'
            })
        }
