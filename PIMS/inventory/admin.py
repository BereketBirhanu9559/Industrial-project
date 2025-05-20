from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile,Inventory,Sale,Transaction
from customer.models import Customer


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


from django.db.models import Sum
from .models import Inventory, Sale

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        'product_name',
        'batch_no',
        'category',
        'quantity',
        'reserved_quantity',
        'remaining_quantity',
        'total_sales_quantity',
        'original_quantity',
        'price',
        'expiry_date',
        'status',
        'shelf_location',
        'created_at',
        'moved_to_pharmacy_date',
        'stock_status',
    )
    list_filter = (
        'category',
        'status',
        'expiry_date',
        'moved_to_pharmacy_date',
    )
    search_fields = (
        'product_name',
        'batch_no',
        'shelf_location',
    )
    list_editable = (
        'quantity',
        'reserved_quantity',
        'price',
        'status',
        'shelf_location',
    )
    date_hierarchy = 'expiry_date'
    ordering = ('-created_at',)
    list_per_page = 20
    actions = ['mark_as_expired', 'mark_as_available']

    def remaining_quantity(self, obj):
        return obj.quantity - obj.reserved_quantity
    remaining_quantity.short_description = "Remaining Quantity"
    remaining_quantity.admin_order_field = 'quantity'

    def total_sales_quantity(self, obj):
        total = obj.sale_set.aggregate(Sum('quantity'))['quantity__sum'] or 0
        return total
    total_sales_quantity.short_description = 'Total Sales Quantity'

    def stock_status(self, obj):
        available = obj.quantity - obj.reserved_quantity
        if available <= 0:
            return "Out of Stock"
        elif available < 10:
            return "Low Stock"
        else:
            return "In Stock"
    stock_status.short_description = "Stock Status"

    def mark_as_expired(self, request, queryset):
        queryset.update(status='expired')
        self.message_user(request, "Selected items marked as expired.")
    mark_as_expired.short_description = "Mark selected items as expired"

    def mark_as_available(self, request, queryset):
        queryset.update(status='available')
        self.message_user(request, "Selected items marked as available.")
    mark_as_available.short_description = "Mark selected items as available"


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_tx_ref',
        'product_name',
        'quantity',
        'total_amount',
        'customer_email',
        'sale_date',
        'status',
    )
    list_filter = (
        'status',
        'sale_date',
        'product__category',
        'transaction__status',
    )
    search_fields = (
        'transaction__tx_ref',
        'customer_email',
        'product__product_name',
    )
    date_hierarchy = 'sale_date'
    ordering = ('-sale_date',)
    list_per_page = 20
    raw_id_fields = ('product', 'transaction')

    def transaction_tx_ref(self, obj):
        return obj.transaction.tx_ref
    transaction_tx_ref.short_description = "Transaction ID"
    transaction_tx_ref.admin_order_field = 'transaction__tx_ref'

    def product_name(self, obj):
        return obj.product.product_name
    product_name.short_description = "Product"
    product_name.admin_order_field = 'product__product_name'

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, "Selected sales marked as completed.")
    mark_as_completed.short_description = "Mark selected sales as completed"

    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
        self.message_user(request, "Selected sales marked as pending.")
    mark_as_pending.short_description = "Mark selected sales as pending"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('tx_ref', 'email', 'total', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tx_ref', 'email')
    ordering = ('-created_at',)