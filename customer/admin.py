from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('name', 'email', 'phone_number')}),
        ('Documents', {'fields': ('competency_document',)}),
        ('Status', {'fields': ('is_verified', 'is_active')}),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    list_display = ('username', 'name', 'email', 'is_verified')
    list_filter = ('is_verified', 'is_active')
    search_fields = ('username', 'name', 'email')
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_staff=False)