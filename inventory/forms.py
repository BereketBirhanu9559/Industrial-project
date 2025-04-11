from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from .models import UserProfile,Inventory

class LoginForm(AuthenticationForm):
    role = forms.ChoiceField(
        choices=[('', 'Select Role')] + UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': 'required'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': 'autofocus'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        role = cleaned_data.get('role')

        if username and password and role:
            # First try standard authentication (handles password hashing)
            user = authenticate(
                username=username,
                password=password,
                request=self.request
            )
            
            if user is None:
                # Fallback: Check if user exists but password didn't match
                try:
                    from .models import User
                    user = User.objects.get(username=username)
                    if not user.check_password(password):
                        raise ValidationError(
                            "Invalid username or password",
                            code='invalid_login'
                        )
                except User.DoesNotExist:
                    raise ValidationError(
                        "Invalid username or password",
                        code='invalid_login'
                    )
            
            # Check if user is active
            if not user.is_active:
                raise ValidationError(
                    "This account is inactive",
                    code='inactive_account'
                )
            
            # Verify role
            try:
                if user.profile.role != role:
                    raise ValidationError(
                        f"This account has {user.profile.get_role_display()} role",
                        code='wrong_role'
                    )
            except UserProfile.DoesNotExist:
                raise ValidationError(
                    "User profile not found",
                    code='no_profile'
                )
            
            # Store the authenticated user
            self.user_cache = user
        
        return cleaned_data


class InventoryRegistrationForm(forms.ModelForm):
    CATEGORY_CHOICES = [
        ('Antibiotics', 'Antibiotics'),
        ('Analgesics', 'Analgesics (Pain Relievers)'),
        ('Antihistamines', 'Antihistamines'),
        ('Antipyretics', 'Antipyretics (Fever Reducers)'),
        ('Hormonal', 'Hormonal Medications'),
        ('Cardiovascular', 'Cardiovascular Drugs'),
        ('Respiratory', 'Respiratory Drugs'),
        ('Gastrointestinal', 'Gastrointestinal Medications'),
        ('Endocrine', 'Endocrine Medications'),
        ('Neurological', 'Neurological Drugs'),
        ('Oncology', 'Oncology Drugs'),
    ]
    
    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    
    class Meta:
        model = Inventory
        fields = ['product_name', 'batch_no', 'quantity', 'expiry_date', 'price', 'category']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-field w-full px-4 py-3 rounded-lg border focus:outline-none'})

class ShelfLocationForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['shelf_location']
        widgets = {
            'shelf_location': forms.TextInput(attrs={
                'class': 'shadow-md appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-green-400',
                'placeholder': 'Enter new shelf location',
                'required': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shelf_location'].label = "New Shelf Location"