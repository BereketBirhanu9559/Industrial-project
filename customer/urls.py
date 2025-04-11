from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
        path('',views.home, name='home'),
        path('customer_login/',views.customer_login, name='customer_login'),
        path('logout/', views.customer_logout, name='customer_logout'),

        # Login page
]
