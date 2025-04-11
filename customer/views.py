from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerLoginForm


def home(request):
    # Product categories data
    categories = [
        {'name': 'Antibiotics', 'icon': 'fas fa-capsules', 'color': 'blue'},
        {'name': 'Vaccines', 'icon': 'fas fa-syringe', 'color': 'green'},
        {'name': 'Chronic Medications', 'icon': 'fas fa-pills', 'color': 'purple'},
        {'name': 'OTC Drugs', 'icon': 'fas fa-medkit', 'color': 'red'}
    ]

    # Featured products data
    products = [
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

    context = {
        'title': 'Wholesale Pharmaceutical Marketplace',
        'categories': categories,
        'products': products,
        'user': request.user
    }
    return render(request, 'home.html', context)


def customer_login(request):
    if request.user.is_authenticated:
        return redirect('home')  # Replace with your dashboard URL
    
    if request.method == 'POST':
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'home')  # Default redirect
                return redirect(next_url)
    else:
        form = CustomerLoginForm()
    
    return render(request, 'customer_login.html', {
        'form': form,
        'title': 'Customer Login'
    })

@login_required
def customer_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect('customer_login')