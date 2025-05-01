from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
        path('',views.home, name='home'),
        path('customer_login/',views.customer_login, name='customer_login'),
        path('logout/', views.customer_logout, name='customer_logout'),
        path('register/', views.initial_registration, name='initial_registration'),
        path('verify/<uuid:token>/', views.verify_customer, name='verify_customer'),
        path('complete/<uuid:token>/', views.complete_registration, name='complete_registration'),
        path('medicines/', views.available_medicines, name='available_medicines'),
        path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
        # Login page
]
