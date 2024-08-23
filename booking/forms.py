from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils.translation import gettext_lazy as _
from .constants import *
from .models import *

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=MAX_LENGTH_NAME, 
        validators=[MinLengthValidator(6), RegexValidator(regex=REGEX_PATTERN)], 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Username')}),
        label=_('Username')
    )
    password = forms.CharField(
        max_length=MAX_LENGTH_NAME, 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Password')}), 
        label=_('Password')
    )

class SignUpForm(forms.ModelForm):
    username = forms.CharField(
        max_length=MAX_LENGTH_NAME, 
        validators=[MinLengthValidator(6), RegexValidator(regex=REGEX_PATTERN)], 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Username')}),
        label=_('Username')
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email')}), 
        label=_('Email')
    )
    phone_number = forms.CharField(
        max_length=20, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Phone Number')}), 
        label=_('Phone Number')
    )
    password = forms.CharField(
        max_length=MAX_LENGTH_NAME, 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Password')}), 
        label=_('Password')
    )
    confirm_password = forms.CharField(
        max_length=MAX_LENGTH_NAME, 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Confirm Password')}), 
        label=_('Confirm Password')
    )

    class Meta:
        model = Account
        fields = ["username", "email", "phone_number", "password"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise ValidationError(_("Password and confirm password are not the same."))

class VerifyEmailForm(forms.Form):
    otp = forms.CharField(
        max_length=6, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('OTP')}), 
        label=_('OTP')
    )

class UpdateAccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['email', 'phone_number', 'first_name', 'last_name', 'gender', 'date_of_birth', 'passport_number', 'nationality']
