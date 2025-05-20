from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'customer'  # Define the customer namespace
urlpatterns = [
        path('',views.home, name='home'),
        path('customer_login/',views.customer_login, name='customer_login'),
        path('logout/', views.customer_logout, name='customer_logout'),
        path('register/', views.initial_registration, name='initial_registration'),
        path('verify/<uuid:token>/', views.verify_customer, name='verify_customer'),
        path('complete/<uuid:token>/', views.complete_registration, name='complete_registration'),
        # Login page
        path('products/', views.items_list, name='items_list'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('debug/session/', views.debug_session, name='debug_session'),
]


        

