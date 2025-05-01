from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from .models import UserProfile,Inventory, Disposal
from django.utils import timezone
from django.db.models import Q
from django.utils.safestring import mark_safe  # Add this import


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

class DisposalForm(forms.ModelForm):
    class Meta:
        model = Disposal
        fields = ['method', 'quantity', 'documentation', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'step': 1
            }),
            # ... other widgets ...
        }
    
    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        if self.product:
            self.fields['quantity'].widget.attrs['max'] = self.product.quantity

class BulkDisposalForm(forms.Form):
    method = forms.ChoiceField(
        choices=Disposal.METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'block w-full px-4 py-2 mt-1 text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm focus:border-red-500 focus:ring focus:ring-red-200 focus:ring-opacity-50'
        })
    )
    documentation = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-red-50 file:text-red-700 hover:file:bg-red-100'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'block w-full px-4 py-2 mt-1 text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm focus:border-red-500 focus:ring focus:ring-red-200 focus:ring-opacity-50',
            'rows': 3
        })
    )
    products = forms.ModelMultipleChoiceField(
        queryset=Inventory.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['products'].queryset = self.get_eligible_products()
            # Override the label_from_instance to show more detailed information
            self.fields['products'].label_from_instance = self.label_from_product

    def get_eligible_products(self):
        """Returns products eligible for bulk disposal"""
        return Inventory.objects.filter(
            Q(expiry_date__lt=timezone.now().date()) | Q(status='expired'),
            status__in=['available', 'pharmacy', 'expired'],
            quantity__gt=0
        ).order_by('expiry_date')

    def label_from_product(self, product):
        """Custom label format for products"""
        return mark_safe(f"""
            <div class="flex justify-between">
                <span class="text-gray-700">{product.product_name}</span>
                <span class="text-xs bg-red-100 text-red-800 px-2 py-1 rounded-full">
                    Exp: {product.expiry_date.strftime('%Y-%m-%d')}
                </span>
            </div>
            <div class="text-xs text-gray-500 mt-1">
                Batch: {product.batch_no} | Qty: {product.quantity} | Location: {product.shelf_location or 'N/A'}
            </div>
        """)