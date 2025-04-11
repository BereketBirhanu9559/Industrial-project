from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_inventory, name='inventory_registration'),
    path('products/',views.product_list, name='product_list'),
    path('products/<int:product_id>/update-shelf/', views.update_shelf_location, name='update_shelf_location'),
    path('logout/', views.logout_view, name='logout'),
    
        # Login page
]
