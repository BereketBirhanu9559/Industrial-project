from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile,Inventory

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fields = ('role', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    extra = 0  # Don't show extra blank forms

    def has_add_permission(self, request, obj=None):
        return False  # Prevent adding new profiles directly through inline

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for the custom User model with UserProfile inline.
    """
    inlines = (UserProfileInline,)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'name', 'email', 'password1', 'password2'),
        }),
    )

    list_display = ('username', 'name', 'email', 'get_role', 'is_staff')
    search_fields = ('username', 'name', 'email', 'profile__role')
    ordering = ('username',)
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        # Create profile if missing (for existing users)
        UserProfile.objects.create(user=obj, role='clerk')
        return obj.profile.get_role_display()
    get_role.short_description = 'Role'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Ensure profile exists after saving user
        if not hasattr(obj, 'profile'):
            UserProfile.objects.create(user=obj, role='clerk')
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_username', 'role', 'created_at', 'updated_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__name', 'role')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)  # Optimize database queries
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = ('product_name', 'batch_no', 'quantity', 'expiry_date', 'price', 'category', 'created_at')
    
    # Enable filtering by these fields
    list_filter = ('category', 'expiry_date', 'created_at')
    
    # Enable search functionality for these fields
    search_fields = ('product_name', 'batch_no', 'category')
    
    # Fields that can be edited directly in the list view
    list_editable = ('quantity', 'price')
    
    # Fields to group in the edit form
    fieldsets = (
        ('Product Information', {
            'fields': ('product_name', 'batch_no', 'category')
        }),
        ('Stock Information', {
            'fields': ('quantity', 'price', 'expiry_date')
        }),
    )
    
    # Date-based navigation/hierarchy
    date_hierarchy = 'expiry_date'
    
    # Automatic slug generation (if you had a slug field)
    # prepopulated_fields = {'slug': ('product_name',)}
    
    # Custom ordering
    ordering = ('-created_at',)
    # Add this to your InventoryAdmin class if you want more features:

# To show a custom column
def remaining_days(self, obj):
    from django.utils import timezone
    remaining = (obj.expiry_date - timezone.now().date()).days
    return remaining if remaining > 0 else "Expired"
remaining_days.short_description = "Days Until Expiry"

# Then add it to list_display
list_display = (..., 'remaining_days')

# To customize the display of empty values
empty_value_display = '-empty-'

# To set the number of items per page
list_per_page = 50

# To add actions
actions = ['mark_as_expired']

def mark_as_expired(self, request, queryset):
    queryset.update(quantity=0)
mark_as_expired.short_description = "Mark selected items as expired (quantity=0)"