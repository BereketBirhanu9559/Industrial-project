from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Customer
from django.contrib.auth import authenticate



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

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # Try authenticating with username or email
            user = authenticate(self.request, username=username, password=password)
            if user is None:
                # Try email-based authentication
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(self.request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if user is None:
                raise forms.ValidationError(
                    "Invalid username/email or password.",
                    code='invalid_login'
                )

            self.user_cache = user
            self.confirm_login_allowed(user)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        # Check if the user has a linked Customer profile
        if not hasattr(user, 'customer'):
            raise forms.ValidationError(
                "This account is not registered as a customer.",
                code='invalid_login'
            )
        
        # Check if user is active
        if not user.is_active:
            raise forms.ValidationError(
                "This account is inactive.",
                code='inactive'
            )
class ProductSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search products',
            'class': 'shadow appearance-none border rounded w-64 py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
        })
    )
    category_filter = forms.ChoiceField(
        required=False,
        choices=[],  # Populated in __init__
        widget=forms.Select(attrs={
            'class': 'shadow appearance-none border rounded w-64 py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            'onchange': 'this.form.submit()'
        })
    )

    def __init__(self, *args, **kwargs):
        categories = kwargs.pop('categories', [])
        super().__init__(*args, **kwargs)
        self.fields['category_filter'].choices = [('', 'All Categories')] + [(c, c) for c in categories]

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'shadow appearance-none border rounded w-20 py-1 px-2 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            'min': '1'
        })
    )
    product_id = forms.IntegerField(widget=forms.HiddenInput())