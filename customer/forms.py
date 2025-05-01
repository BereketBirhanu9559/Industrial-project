from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Customer


class InitialRegistrationForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'temp_email', 'competency_document', 'phone_number']
        widgets = {
            'competency_document': forms.FileInput(attrs={'accept': '.pdf,.jpg,.png'})
        }

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class CredentialSetupForm(forms.Form):
    username = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username is already taken. Please choose another one.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 != password2:
            raise forms.ValidationError('Passwords do not match.')

        return cleaned_data

class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input-field w-full pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white border-2 border-white/30 focus:outline-none',
            'placeholder': 'Enter your username or email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field w-full pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white border-2 border-white/30 focus:outline-none',
            'placeholder': 'Enter your password'
        })
    )

    def confirm_login_allowed(self, user):
        # Check if the user has a linked Customer profile
        if not hasattr(user, 'customer'):
            raise forms.ValidationError(
                "This account is not registered as a customer.",
                code='invalid_login'
            )
        
        # Optional: check if user is active
        if not user.is_active:
            raise forms.ValidationError(
                "This account is inactive.",
                code='inactive'
            )
