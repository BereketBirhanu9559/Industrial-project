from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from .forms import InitialRegistrationForm, CredentialSetupForm,CustomerLoginForm
from .models import Customer
from inventory.models import Inventory  # Import Inventory model from inventory app


from django.db.models import Q

def home(request):
    # Product categories data from the model
    categories = Inventory.CATEGORY_CHOICES  # Fetch categories from model
    
    # Featured products data
    featured_products = [
        {
            'name': 'Amoxicillin Bulk Pack',
            'description': 'Antibiotic for Bulk Distribution',
            'price': 10000,
            'min_order': 100,
            'image': 'https://media.istockphoto.com/id/1161324758/photo/red-yellow-capsule-in-blister-pack-antibiotic-capsule-pills-antimicrobial-drug-resistance.jpg?s=1024x1024&w=is&k=20&c=BPcY3uPIK66wH-cj9OC1IQcVTHgbfwl4helRxs-yqPQ='
        },
        {
            'name': 'Artemisinin-based Combination Therapy (ACT)',
            'description': 'Malaria Treatment',
            'price': 12000,
            'min_order': 500,
            'image': 'https://media.istockphoto.com/id/1212172718/photo/doctor-holding-chloroquine-phosphate-drug.jpg?s=1024x1024&w=is&k=20&c=T7Rbn4YFp7ZTsg5uFJSceWLVossSylo846N2hgMCrww='
        },
        {
            'name': 'Paracetamol',
            'description': 'used to treat mild to moderate pain',
            'price': 18000,
            'min_order': 250,
            'image': 'https://media.istockphoto.com/id/1359178149/photo/acetaminophen-ibuprofeno-pill-box-box-paper-blister-tablets.jpg?s=1024x1024&w=is&k=20&c=HKsN0y-S2WUrkc3UbhPhz-bvg2mRwb4dxtPZtvtrs6Q='
        }
    ]

    # For authenticated users - add medicines data
    medicines = None
    search = ''
    category_filter = ''
    
    if request.user.is_authenticated:
        medicines = Inventory.objects.all()  # Get all medicines or filter as needed
        
        # Handle search and filter
        if request.method == 'POST':
            search = request.POST.get('search', '')
            category_filter = request.POST.get('category_filter', '')
            
            if search:
                medicines = medicines.filter(
                    Q(product_name__icontains=search) |  # Filter by product name
                    Q(batch_no__icontains=search)        # Or filter by batch number
                )
            if category_filter:
                medicines = medicines.filter(category=category_filter)

    context = {
        'title': 'Wholesale Pharmaceutical Marketplace',
        'categories': categories,  # Use categories from model
        'featured_products': featured_products,  # Changed from 'products' to match template
        'user': request.user,
        'medicines': medicines,  # For authenticated users
        'search': search,  # For search persistence
        'category_filter': category_filter,  # For filter persistence
    }
    return render(request, 'home.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .models import Customer
from .forms import InitialRegistrationForm, CredentialSetupForm, CustomerLoginForm
from django.contrib.auth import get_user_model

User = get_user_model()  # Always use this to refer to the custom User

def initial_registration(request):
    if request.method == 'POST':
        form = InitialRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.status = Customer.PENDING
            customer.save()
            messages.success(request, 'Registration submitted! Our team will review your documents.')
            return redirect('initial_registration')
    else:
        form = InitialRegistrationForm()
    return render(request, 'initial_register.html', {'form': form})

def verify_customer(request, token):
    customer = get_object_or_404(
        Customer, 
        verification_token=token,
        status=Customer.APPROVED
    )
    
    if hasattr(customer, 'user') and customer.user:  # Already linked
        messages.info(request, 'Account already verified')
        return redirect('complete_registration', token=token)
    
    customer.status = Customer.VERIFIED
    customer.save()
    
    messages.success(request, 'Email verified! Please set your credentials')
    return redirect('complete_registration', token=token)

def complete_registration(request, token):
    customer = get_object_or_404(
        Customer,
        verification_token=token,
        status=Customer.VERIFIED
    )
    
    if request.method == 'POST':
        form = CredentialSetupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            # Create User and link to Customer
            user = User.objects.create_user(
                username=username,
                password=password,
                email=customer.temp_email,
                name=customer.name,
                is_active=True  # Make active after account creation
            )
            customer.user = user
            customer.save()

            messages.success(request, 'Registration complete! You can now login.')
            return redirect('customer_login')
    else:
        form = CredentialSetupForm()
    
    return render(request, 'complete_register.html', {
        'form': form,
        'email': customer.temp_email
    })

def customer_login(request):
    if request.user.is_authenticated:
        return redirect('home')  # Replace with your dashboard URL
    
    if request.method == 'POST':
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Authenticate normally
            user = authenticate(request, username=username_or_email, password=password)

            # If normal username fails, try matching by email
            if user is None:
                try:
                    # Find User by email
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'home')  # Default redirect
                return redirect(next_url)
            else:
                form.add_error(None, "Invalid username/email or password")
    else:
        form = CustomerLoginForm()
    
    return render(request, 'customer_login.html', {
        'form': form,
        'title': 'Customer Login'
    })

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from inventory.models import Inventory


from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect
from inventory.models import Inventory


@login_required
def available_medicines(request):
    # Get search and filter parameters
    search = request.POST.get('search', '').strip()  # Search term from POST request
    category_filter = request.GET.get('category_filter', '').strip()  # Category filter from GET request

    # Start with all inventory items
    medicines = Inventory.objects.all()

    # Apply search filter if search term is present
    if search:
        medicines = medicines.filter(
            Q(product_name__icontains=search) |  # Filter by product name
            Q(batch_no__icontains=search)        # Or filter by batch number
        )

    # Apply category filter if category filter is selected
    if category_filter:
        medicines = medicines.filter(category=category_filter)

    # Get unique categories for dropdown menu
    categories = Inventory.objects.values_list('category', flat=True).distinct()

    # Pass the filtered medicines and categories to the template
    context = {
        'title': 'Available Medicines',
        'medicines': medicines,
        'categories': categories,  # List of available categories
        'search': search,          # Search term to retain in input field
        'category_filter': category_filter,  # Selected category filter
    }

    # Render the template with context data
    return render(request, 'customers/available_medicines.html', context)


@login_required
def add_to_cart(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    
    try:
        product = Inventory.objects.get(id=product_id)
        
        # Check available quantity
        if quantity > product.quantity:
            messages.error(request, "Requested quantity exceeds available stock. Please adjust your quantity.")
            return redirect('available_medicines')
        
        # Initialize cart if it doesn't exist
        if 'order_items' not in request.session:
            request.session['order_items'] = []
        
        # Add item to cart
        request.session['order_items'].append({
            'product_id': product.id,
            'product_name': product.product_name,
            'price': float(product.price),
            'quantity': quantity,
            'total': float(product.price) * quantity,
        })
        request.session.modified = True
        
        messages.success(request, "Item added to cart successfully!")
        return redirect('available_medicines')
    
    except Inventory.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect('available_medicines')

@login_required
def customer_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect('customer_login')