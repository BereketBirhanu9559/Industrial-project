from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_inventory, name='inventory_registration'),
    path('products/',views.product_list, name='product_list'),
    path('products/<int:product_id>/update-shelf/', views.update_shelf_location, name='update_shelf_location'),
    path('inventory/expired/', views.ExpiredProductsView.as_view(), name='expired_products'),
    path('inventory/<int:pk>/',views.ProductDetailView.as_view(), name='product_detail'),
    path('inventory/<int:pk>/dispose/', views.DisposalCreateView.as_view(), name='dispose_product'),
    path('inventory/bulk-dispose/', views.BulkDisposalView.as_view(), name='bulk_dispose'),
    path('inventory/export-expired/', views.export_expired_csv, name='export_expired_csv'),
    path('inventory/near-expiry/', views.NearExpiryListView.as_view(), name='near_expiry_list'),
    path('inventory/<int:pk>/loan/', views.CreatePharmacyLoanView.as_view(), name='create_pharmacy_loan'),
    path('pharmacy-loan/<int:pk>/update/', views.UpdatePharmacyLoanView.as_view(), name='update_pharmacy_loan'),
    path('pharmacy-loans/', views.PharmacyLoansListView.as_view(), name='pharmacy_loans_list'),
    path('pharmacy-loan/<int:pk>/', views.PharmacyLoanDetailView.as_view(), name='pharmacy_loan_detail'),
    path('logout/', views.logout_view, name='logout'),
    
        # Login page
]
