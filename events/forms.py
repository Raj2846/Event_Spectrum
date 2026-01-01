# events/forms.py
from django import forms
from django.core.validators import RegexValidator
import re

class TicketBookingForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        }),
        error_messages={
            'required': 'Please enter your full name',
            'max_length': 'Name must be less than 100 characters'
        }
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        }),
        error_messages={
            'required': 'Please enter your email address',
            'invalid': 'Please enter a valid email address'
        }
    )
    
    phone_validator = RegexValidator(
        regex=r'^[6-9]\d{9}$',
        message='Please enter a valid 10-digit Indian mobile number'
    )
    
    phone = forms.CharField(
        max_length=10,
        required=True,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10-digit mobile number'
        }),
        error_messages={
            'required': 'Please enter your phone number'
        }
    )
    
    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if not name:
            raise forms.ValidationError('Name cannot be empty')
        if len(name) < 3:
            raise forms.ValidationError('Name must be at least 3 characters long')
        if not re.match(r'^[a-zA-Z\s]+$', name):
            raise forms.ValidationError('Name can only contain letters and spaces')
        return name
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if not email:
            raise forms.ValidationError('Email cannot be empty')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError('Phone number cannot be empty')
        if not phone.isdigit():
            raise forms.ValidationError('Phone number must contain only digits')
        return phone