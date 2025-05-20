import json
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from .forms import InitialRegistrationForm, CredentialSetupForm,CustomerLoginForm,ProductSearchForm, AddToCartForm
from .models import Customer
from inventory.models import Inventory,Sale,Transaction
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from django.urls import reverse
import requests
import uuid
import logging


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
        return redirect('customer:items_list')  # Replace with your dashboard URL
    
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
                next_url = request.GET.get('next', 'customer:items_list')  # Default redirect
                return redirect(next_url)
            else:
                form.add_error(None, "Invalid username/email or password")
    else:
        form = CustomerLoginForm()
    
    return render(request, 'customer_login.html', {
        'form': form,
        'title': 'Customer Login'
    })



"""
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
"""

@login_required
def items_list(request):
    # Get categories for filter dropdown
    categories = Inventory.objects.values_list('category', flat=True).distinct()
    
    # Initialize forms
    search_form = ProductSearchForm(request.POST or None, categories=categories)
    add_to_cart_form = AddToCartForm(request.POST or None)
    
    # Start with all products
    products = Inventory.objects.all()
    
    # Apply search/filters
    if search_form.is_valid():
        search = search_form.cleaned_data['search']
        category_filter = search_form.cleaned_data['category_filter']
        
        if search:
            products = products.filter(
                Q(product_name__icontains=search) |
                Q(category__icontains=search)
            )    
        if category_filter:
            products = products.filter(category=category_filter)
    

    context = {
        'products': products,
        'search_form': search_form,
        'categories': categories,
        'cart': request.session.get('cart', {}),
    }
    return render(request, 'product_list.html', context)

logger = logging.getLogger(__name__)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Inventory, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    cart = request.session.get('cart', {})
    available_quantity = product.quantity - product.reserved_quantity
    if quantity > available_quantity:
        messages.error(request, f"Not enough stock available! Only {available_quantity} {product.product_name}(s) available.")
        return redirect('customer:items_list')
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    request.session['cart'] = cart
    request.session.modified = True
    logger.info(f"Added to cart: product_id={product_id}, quantity={quantity}, cart={cart}, session_id={request.session.session_key}")
    messages.success(request, f"{product.product_name} added to cart!")
    return redirect('customer:items_list')

@login_required
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = get_object_or_404(Inventory, id=product_id)
        item_total = product.price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total': item_total
        })
        total += item_total
    logger.info(f"Viewing cart: cart={cart}, total={total}, session_id={request.session.session_key}")
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'grand_total': total
    })

@login_required
def update_cart(request, product_id):
    product = get_object_or_404(Inventory, id=product_id)
    cart = request.session.get('cart', {})
    if request.GET.get('remove') == 'true':
        if str(product_id) in cart:
            del cart[str(product_id)]
            messages.success(request, f"Removed {product.product_name} from cart.")
        request.session['cart'] = cart
        request.session.modified = True
        logger.info(f"Removed from cart: product_id={product_id}, cart={cart}, session_id={request.session.session_key}")
        return redirect('customer:view_cart')
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity <= 0:
                cart.pop(str(product_id), None)
                messages.success(request, f"Removed {product.product_name} from cart.")
            else:
                available_quantity = product.quantity - product.reserved_quantity
                if quantity > available_quantity:
                    messages.error(request, f"Insufficient stock! Only {available_quantity} {product.product_name}(s) available.")
                else:
                    cart[str(product_id)] = quantity
                    messages.success(request, f"Updated {product.product_name} quantity to {quantity}.")
            request.session['cart'] = cart
            request.session.modified = True
            logger.info(f"Updated cart: product_id={product_id}, quantity={quantity}, cart={cart}, session_id={request.session.session_key}")
        except ValueError:
            messages.error(request, "Please enter a valid quantity.")
    return redirect('customer:view_cart')

@login_required
def initiate_payment(request):
    cart = request.session.get('cart', {})
    logger.info(f"Initiate payment: cart={cart}, session_id={request.session.session_key}, session_keys={list(request.session.keys())}")
    if not cart:
        messages.error(request, "Your cart is empty!")
        logger.error("Initiate payment failed: Empty cart")
        return redirect('customer:view_cart')
    cart_items = []
    total = 0
    with transaction.atomic():
        for product_id, quantity in cart.items():
            product = get_object_or_404(Inventory, id=product_id)
            available_quantity = product.quantity - product.reserved_quantity
            if quantity > available_quantity:
                messages.error(request, f"Insufficient stock for {product.product_name}! Only {available_quantity} available.")
                logger.error(f"Insufficient stock: product={product.product_name}, requested={quantity}, available={available_quantity}")
                return redirect('customer:view_cart')
            if not product.reserve_quantity(quantity):
                messages.error(request, f"Failed to reserve {product.product_name}.")
                logger.error(f"Failed to reserve: product={product.product_name}, quantity={quantity}")
                return redirect('customer:view_cart')
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    tx_ref = f"PHARM-{uuid.uuid4().hex[:10]}"
    email = request.POST.get('customer_email', request.user.email if request.user.is_authenticated else 'customer@example.com')
    
    # Save to Transaction model
    transaction_obj = Transaction.objects.create(
        tx_ref=tx_ref,
        total=float(total),
        email=email,
        status='pending'
    )
    transaction_obj.set_cart(cart)
    transaction_obj.save()
    
    # Save to session for redundancy
    payment_details = {
        'tx_ref': tx_ref,
        'cart': cart,
        'total': float(total),
        'email': email,
    }
    request.session['payment_details'] = payment_details
    request.session['cart'] = cart
    request.session.modified = True
    logger.info(f"Payment details saved: tx_ref={tx_ref}, total={total}, cart={cart}, email={email}, session_id={request.session.session_key}, session_keys={list(request.session.keys())}, transaction_id={transaction_obj.id}")
    
    chapa_payload = {
        "amount": float(total),
        "currency": "ETB",
        "email": email,
        "tx_ref": tx_ref,
        "callback_url": request.build_absolute_uri(reverse('customer:payment_callback')),
        "return_url": request.build_absolute_uri(reverse('customer:payment_success')),
        "first_name": request.user.first_name if request.user.is_authenticated else "Customer",
        "last_name": request.user.last_name if request.user.is_authenticated else "",
        "title": "Pharmacy Order",
        "description": "Payment for pharmacy products",
    }
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(
            "https://api.chapa.co/v1/transaction/initialize",
            json=chapa_payload,
            headers=headers
        )
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"Chapa initialize response: {response_data}, callback_url={chapa_payload['callback_url']}")
        if response_data.get('status') == 'success':
            return redirect(response_data['data']['checkout_url'])
        else:
            for product_id, quantity in cart.items():
                product = get_object_or_404(Inventory, id=product_id)
                product.release_reserved_quantity(quantity)
            transaction_obj.status = 'failed'
            transaction_obj.save()
            messages.error(request, f"Failed to initiate payment: {response_data.get('message', 'Unknown error')}")
            logger.error(f"Chapa initialize failed: {response_data.get('message', 'Unknown error')}")
            return redirect('customer:view_cart')
    except requests.RequestException as e:
        logger.error(f"Payment initiation failed: {str(e)}")
        for product_id, quantity in cart.items():
            product = get_object_or_404(Inventory, id=product_id)
            product.release_reserved_quantity(quantity)
        transaction_obj.status = 'failed'
        transaction_obj.save()
        messages.error(request, f"Payment initiation failed: {str(e)}")
        return redirect('customer:view_cart')


@csrf_exempt  # Chapa's callback doesn't send CSRF token

def payment_callback(request):
    logger.info(f"Payment callback triggered: query_params={request.GET}, session_id={request.session.session_key}")
    tx_ref = request.GET.get('trx_ref')
    
    if not tx_ref:
        logger.error("Missing tx_ref in query parameters")
        messages.error(request, "Invalid payment session.")
        return redirect('customer:view_cart')

    try:
        transaction_obj = Transaction.objects.get(tx_ref=tx_ref)
        cart = transaction_obj.get_cart()
        payment_details = {
            'tx_ref': tx_ref,
            'cart': cart,
            'total': float(transaction_obj.total),
            'email': transaction_obj.email,
        }
    except Transaction.DoesNotExist:
        logger.error(f"No transaction found for tx_ref={tx_ref}")
        messages.error(request, "Transaction not found.")
        return redirect('customer:view_cart')

    # Check if transaction is already completed
    if transaction_obj.status == 'completed':
        logger.info(f"Transaction already completed: tx_ref={tx_ref}")
        request.session['cart'] = {}
        request.session['payment_details'] = {}
        request.session.modified = True
        logger.info(f"Cart cleared: cart={request.session['cart']}, payment_details={request.session['payment_details']}")
        messages.success(request, "Payment already processed.")
        return redirect('customer:payment_success')

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
    }
    try:
        response = requests.get(
            f"https://api.chapa.co/v1/transaction/verify/{tx_ref}",
            headers=headers
        )
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"Chapa verify response: status={response_data.get('status')}")

        if response_data.get('status') == 'success':
            with transaction.atomic():
                # Update transaction status first
                transaction_obj.status = 'completed'
                transaction_obj.save()
                
                # Create Sale records for each cart item
                for product_id, quantity in cart.items():
                    product = get_object_or_404(Inventory, id=product_id)
                    # Check if Sale already exists for this product and transaction
                    if not Sale.objects.filter(transaction=transaction_obj, product=product).exists():
                        if not product.deduct_quantity(quantity):
                            logger.error(f"Stock issue: product={product.product_name}")
                            messages.error(request, f"Stock issue with {product.product_name}.")
                            transaction_obj.status = 'failed'
                            transaction_obj.save()
                            return redirect('customer:view_cart')
                        Sale.objects.create(
                            product=product,
                            quantity=quantity,
                            total_amount=product.price * quantity,
                            transaction=transaction_obj,  # Use Transaction object
                            customer_email=transaction_obj.email,
                            status='completed'
                        )
                        logger.info(f"Sale recorded: product={product.product_name}, quantity={quantity}")
                
                # Clear cart
                request.session['cart'] = {}
                request.session['payment_details'] = {}
                request.session.modified = True
                logger.info(f"Cart cleared: cart={request.session['cart']}, payment_details={request.session['payment_details']}")
                messages.success(request, "Payment successful!")
                return redirect('customer:payment_success')
        else:
            logger.warning(f"Payment failed: tx_ref={tx_ref}")
            for product_id, quantity in cart.items():
                product = get_object_or_404(Inventory, id=product_id)
                product.release_reserved_quantity(quantity)
            transaction_obj.status = 'failed'
            transaction_obj.save()
            messages.error(request, "Payment failed.")
            return redirect('customer:view_cart')
    except requests.RequestException as e:
        logger.error(f"Chapa API error: tx_ref={tx_ref}, error={str(e)}")
        for product_id, quantity in cart.items():
            product = get_object_or_404(Inventory, id=product_id)
            product.release_reserved_quantity(quantity)
        transaction_obj.status = 'failed'
        transaction_obj.save()
        messages.error(request, f"Payment verification failed.")
        return redirect('customer:view_cart')

def payment_success(request):
    if request.session.get('cart') or request.session.get('payment_details'):
        request.session['cart'] = {}
        request.session['payment_details'] = {}
        request.session.modified = True
        logger.info(f"Residual cart cleared in payment_success: cart={request.session['cart']}, payment_details={request.session['payment_details']}")
    
    logger.info("Rendering payment success page")
    return render(request, 'payment_success.html', {
        'message': 'Payment successful! Your cart has been cleared.'
    })

def debug_session(request):
    return render(request, 'debug_session.html', {
        'session_keys': request.session.keys(),
        'payment_details': request.session.get('payment_details'),
        'cart': request.session.get('cart'),
        'session_id': request.session.session_key,
    })


@login_required
def customer_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect('customer:customer_login')

