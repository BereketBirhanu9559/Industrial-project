from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login as auth_login, logout
from django.contrib import messages
from .forms import LoginForm,InventoryRegistrationForm,ShelfLocationForm
from .models import UserProfile,Inventory
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login as auth_login, logout
from django.contrib import messages
from .forms import LoginForm,InventoryRegistrationForm,ShelfLocationForm,DisposalForm,BulkDisposalForm
from django.db.models import Q
from .models import UserProfile,Inventory,Disposal,PharmacyLoan
from django.views.generic import ListView, DetailView, FormView, UpdateView
from django.utils import timezone
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.edit import CreateView
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse
import csv
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
# With this:



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

def update_shelf_location(request, product_id):
    product = get_object_or_404(Inventory, id=product_id)
    
    if request.method == 'POST':
        form = ShelfLocationForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Shelf location updated successfully!")
            return redirect('product_list')
    else:
        form = ShelfLocationForm(instance=product)
    
    return render(request, 'clerk/update_shelf_location.html', {
        'product': product,
        'form': form
    })
1
class ExpiredProductsView(ListView):
    model = Inventory
    template_name = 'regulatory/expired_products.html'
    context_object_name = 'expired_products'
    
    def get_queryset(self):
        return Inventory.objects.filter(
            Q(expiry_date__lt=timezone.now().date()) | 
            Q(status='expired')
        ).order_by('expiry_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now().date()  # Add current date to context
        context['current_date'] = timezone.now().date()  # Alternative name if template uses this
        return context
class ProductDetailView(DetailView):
    model = Inventory
    template_name = 'regulatory/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['disposals'] = Disposal.objects.filter(inventory=self.object)
        context['current_date'] = timezone.now().date()  # Add this line
        return context


class DisposalCreateView(CreateView):
    model = Disposal
    form_class = DisposalForm
    template_name = 'regulatory/dispose_product.html'

    def get_form_kwargs(self):
        """Pass the product to the form for quantity validation"""
        kwargs = super().get_form_kwargs()
        kwargs['product'] = self.get_product()
        return kwargs

    def get_product(self):
        """Helper method to get the current product"""
        return Inventory.objects.get(pk=self.kwargs['pk'])

    def form_valid(self, form):
        product = self.get_product()
        disposal_quantity = form.cleaned_data['quantity']

        # Validate disposal quantity
        if disposal_quantity <= 0:
            form.add_error('quantity', 'Disposal quantity must be positive')
            return self.form_invalid(form)

        # Check against available quantity (returned - already disposed)
        available_for_disposal = product.returned_quantity - product.total_disposed
        if disposal_quantity > available_for_disposal:
            form.add_error('quantity',
                f'Cannot dispose more than available quantity ({available_for_disposal})')
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                # Create disposal record
                disposal = form.save(commit=False)
                disposal.inventory = product
                disposal.documented_by = self.request.user
                disposal.witnessed_by = self.request.user
                disposal.save()  # Inventory updates happen in Disposal.save()

                # Refresh inventory info after saving
                product.refresh_from_db()

                # Compute remaining_after for use in template (returned - total disposed after this disposal)
                disposal.remaining_after = product.returned_quantity - product.total_disposed

                # Set success message
                if product.status == 'disposed':
                    msg = f"Fully disposed {disposal_quantity} units. Product is now marked as disposed."
                else:
                    remaining = product.returned_quantity - product.total_disposed
                    msg = (f"Disposed {disposal_quantity} units successfully. "
                          f"{remaining} units remain available for disposal.")

                messages.success(self.request, msg)

        except Exception as e:
            messages.error(self.request, f"Error during disposal: {str(e)}")
            return redirect('product_detail', pk=product.pk)

        return redirect('product_detail', pk=product.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_product()
        disposals = product.disposal_set.all().order_by('-disposal_date')

        # Calculate remaining after each disposal for historical context
        running_disposed = 0
        for disposal in disposals:
            running_disposed += disposal.quantity
            disposal.remaining_after = product.returned_quantity - running_disposed

        context.update({
            'product': product,
            'remaining_quantity': product.returned_quantity - product.total_disposed,
            'can_dispose': (product.returned_quantity - product.total_disposed) > 0 
                           and product.status != 'disposed',
            'disposals': disposals,
        })
        return context
class BulkDisposalView(FormView):
    form_class = BulkDisposalForm
    template_name = 'regulatory/bulk_dispose.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        method = form.cleaned_data['method']
        notes = form.cleaned_data['notes']
        documentation = form.cleaned_data['documentation']
        
        with transaction.atomic():
            for product in form.cleaned_data['products']:
                Disposal.objects.create(
                    inventory=product,
                    method=method,
                    quantity=product.quantity,
                    witnessed_by=self.request.user,
                    documented_by=self.request.user,
                    documentation=documentation,
                    notes=notes
                )
                product.status = 'disposed'
                product.save()
                
        messages.success(self.request, f"Bulk disposal of {len(form.cleaned_data['products'])} products completed")
        return redirect('expired_products')

def export_expired_csv(request):
    expired_products = Inventory.objects.filter(
        Q(expiry_date__lt=timezone.now().date()) | 
        Q(status='expired')
    ).order_by('expiry_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expired_products.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Product Name', 'Batch Number', 'Category', 
        'Expiry Date', 'Days Expired', 'Quantity', 
        'Status', 'Shelf Location'
    ])

    for product in expired_products:
        days_expired = (timezone.now().date() - product.expiry_date).days
        writer.writerow([
            product.product_name,
            product.batch_no,
            product.get_category_display(),
            product.expiry_date.strftime('%Y-%m-%d'),
            abs(days_expired),
            product.quantity,
            product.get_status_display(),
            product.shelf_location or ''
        ])

    return response

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect('login')



class NearExpiryListView(ListView):
    model = Inventory
    template_name = 'regulatory/near_expiry_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        return Inventory.get_near_expiry_products()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = context['products']
        
        if products.exists() and not self.request.session.get('email_sent', False):
            try:
                self.send_expiry_alert(products)
                self.request.session['email_sent'] = True
                messages.success(self.request, "Regulatory team notified about expiring products")
            except Exception as e:
                messages.error(self.request, f"Could not send alerts: {str(e)}")
        return context
    
    def send_expiry_alert(self, products):
        """Send email alert to regulatory users"""
        try:
            # Get the custom User model
            User = get_user_model()
            
            # Get all users in the Regulatory group
            regulatory_users = User.objects.filter(
                groups__name='Regulatory',
                is_active=True
            )
            
            if not regulatory_users.exists():
                raise Exception("No active users in Regulatory group")
                
            subject = f"⚠️ {products.count()} Products Nearing Expiry"
            
            product_list = "\n".join(
                f"- {p.product_name} (Batch: {p.batch_no}) - Expires: {p.expiry_date} ({p.days_until_expiry} days left)"
                for p in products[:10]
            )
            
            if products.count() > 10:
                product_list += f"\n...and {products.count() - 10} more"
            
            message = f"""
            Products Nearing Expiry:
            
            {product_list}
            
            View in system: {self.request.build_absolute_uri('/inventory/near-expiry/')}
            """
            
            recipient_list = [user.email for user in regulatory_users if user.email]
            
            if not recipient_list:
                raise Exception("No email addresses found for regulatory users")
            
            # Test email configuration first
            try:
                from django.core import mail
                connection = mail.get_connection()
                connection.open()  # Try to open connection
                connection.close()
            except Exception as e:
                raise Exception(f"Email server connection failed: {str(e)}")
            
            # If connection test passed, send the actual email
            send_mail(
                subject=subject,
                message=message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=False
            )
            
        except Exception as e:
            raise Exception(f"Alert sending failed: {str(e)}")
class CreatePharmacyLoanView(CreateView):
    model = PharmacyLoan
    fields = ['pharmacy_name', 'contact_person', 'contact_phone', 'quantity_loaned', 'notes']
    template_name = 'regulatory/create_pharmacy_loan.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = Inventory.objects.get(pk=self.kwargs['pk'])
        return context
    
    def form_valid(self, form):
        product = Inventory.objects.get(pk=self.kwargs['pk'])
        loan = form.save(commit=False)
        loan.inventory = product
        
        if loan.quantity_loaned > product.quantity:
            form.add_error('quantity_loaned', 
                         f"Cannot loan more than available quantity ({product.quantity})")
            return self.form_invalid(form)
        
        with transaction.atomic():
            loan.save()
            product.quantity -= loan.quantity_loaned
            product.save()
            
        messages.success(self.request, 
                       f"{loan.quantity_loaned} units loaned to {loan.pharmacy_name}")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('near_expiry_list')

class UpdatePharmacyLoanView(UpdateView):
    model = PharmacyLoan
    fields = ['quantity_sold', 'quantity_returned', 'status', 'notes', 'return_date']  # Add return_date to fields
    template_name = 'regulatory/update_pharmacy_loan.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        loan = self.object
        form.fields['quantity_sold'].widget.attrs['max'] = loan.quantity_loaned - loan.quantity_returned
        form.fields['quantity_returned'].widget.attrs['max'] = loan.quantity_loaned - loan.quantity_sold

        # Set initial value for return_date if quantity_returned > 0
        if loan.quantity_returned > 0:
            form.fields['return_date'].initial = loan.return_date

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.object
        context.update({
            'loan': loan,
            'max_sold': loan.quantity_loaned - loan.quantity_returned,
            'max_returned': loan.quantity_loaned - loan.quantity_sold,
        })
        return context

    def form_valid(self, form):
        loan = form.save(commit=False)
        product = loan.inventory

        new_quantity_sold = form.cleaned_data['quantity_sold']
        new_quantity_returned = form.cleaned_data['quantity_returned']
        total = new_quantity_sold + new_quantity_returned

        if new_quantity_sold < 0 or new_quantity_returned < 0 or total > loan.quantity_loaned:
            form.add_error(None, "Invalid quantities.")
            return self.form_invalid(form)

        with transaction.atomic():
            if new_quantity_returned > 0 and loan.status == 'returned':
                delta_returned = new_quantity_returned - loan.quantity_returned
                product.quantity += delta_returned
                product.save()
                loan.return_date = timezone.now().date()

            loan.save()

        messages.success(self.request, "Pharmacy loan updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pharmacy_loan_detail', kwargs={'pk': self.object.pk})


class PharmacyLoansListView(ListView):
    model = PharmacyLoan
    template_name = 'regulatory/pharmacy_loans_list.html'
    context_object_name = 'loans'
    ordering = ['-loan_date']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('inventory')
        status = self.request.GET.get('status')

        # Apply filtering based on the 'status' parameter in the URL
        if status == 'on_loan':
            queryset = queryset.filter(quantity_sold=0, quantity_returned=0)
        elif status == 'sold':
            queryset = queryset.filter(quantity_sold__gt=0)
        elif status == 'returned':
            queryset = queryset.filter(quantity_returned__gt=0)

        return queryset

    def get_context_data(self, **kwargs):
        # Get the default context
        context = super().get_context_data(**kwargs)

        # Add the status filter to the context for rendering the current filter in the template
        context['status_filter'] = self.request.GET.get('status', '')
        return context



class PharmacyLoanDetailView(DetailView):
    model = PharmacyLoan
    template_name = 'regulatory/pharmacy_loan_detail.html'
    context_object_name = 'loan'

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect('login')