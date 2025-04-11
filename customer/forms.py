from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Customer


'''class RegistrationApplicationForm(forms.ModelForm):
    required_documents = forms.FileField(
        label='Required Documents',
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
        help_text='Upload all required documents (ID, business license, etc.)'
    )
    
    class Meta:
        model = RegistrationApplication
        fields = ['full_name', 'email', 'phone', 'business_name', 
                 'business_address', 'required_documents', 'additional_notes']
        widgets = {
            'additional_notes': forms.Textarea(attrs={'rows': 4}),
        }

'''

class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input-field w-full pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white border-2 border-white/30 focus:outline-none',
            'placeholder': 'Enter your username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field w-full pl-10 pr-4 py-3 rounded-lg bg-white/20 text-white border-2 border-white/30 focus:outline-none',
            'placeholder': 'Enter your password'
        })
    )

    def confirm_login_allowed(self, user):
        if not isinstance(user, Customer):
            raise forms.ValidationError(
                "This account is not authorized as a customer",
                code='invalid_login'
            )

