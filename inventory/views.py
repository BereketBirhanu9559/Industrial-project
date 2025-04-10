from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout
from django.contrib import messages
from django.contrib.auth import authenticate
from .forms import LoginForm,InventoryRegistrationForm
from django.db.models import Q
from .models import UserProfile,Inventory



@login_required
def index(request):
    user = request.user

    # Access role via profile
    if hasattr(user, 'profile'):
        role = user.profile.role
    else:
        role = None

    context = {
        'user': user,
        'role': role
    }

    return render(request, 'index.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            
            # Set session expiry (optional)
            if not request.POST.get('remember-me'):
                request.session.set_expiry(0)  # Session expires when browser closes
            
            messages.success(request, f"Welcome back, {user.name or user.username}!")
            return redirect('index')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {
        'form': form,
        'title': 'Login',
    })


def register_inventory(request):
    if request.method == 'POST':
        form = InventoryRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('inventory_registration')
        else:
            messages.error(request, 'Failed to add product. Please check the form.')
    else:
        form = InventoryRegistrationForm()
    
    return render(request, 'clerk/registration.html', {'form': form})


@login_required
def product_list(request):
    # Get search and filter parameters
    search = request.POST.get('search', '').strip()
    category_filter = request.POST.get('category_filter', '').strip()

    # Start with all products
    products = Inventory.objects.all()

    # Apply search filter
    if search:
        products = products.filter(
            Q(product_name__icontains=search) |
            Q(batch_no__icontains=search) |
            Q(category__icontains=search)
        )

    # Apply category filter
    if category_filter:
        products = products.filter(category=category_filter)

    # Get unique categories for dropdown
    categories = Inventory.objects.values_list('category', flat=True).distinct()

    context = {
        'products': products,
        'categories': categories,
        'search': search,
        'category_filter': category_filter,
    }
    return render(request, 'clerk/product_list.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect('login')