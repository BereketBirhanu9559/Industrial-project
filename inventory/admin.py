from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from .models import User, UserProfile, Inventory, Disposal,PharmacyLoan

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
    list_select_related = ('profile',)
    
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
    list_select_related = ('user',)
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        'product_name', 
        'batch_no', 
        'original_quantity',
        'total_disposed',
        'remaining_quantity',
        'expiry_date', 
        'expiry_status',
        'price',
        'category', 
        'shelf_location', 
        'status',
        'created_at',
    )
    
    list_filter = (
        'category', 
        'status',
        'expiry_date', 
        'created_at', 
        'shelf_location',
        ('expiry_date', admin.DateFieldListFilter),
    )
    
    search_fields = (
        'product_name', 
        'batch_no', 
        'category', 
        'shelf_location'
    )
    
    list_editable = (
        'price', 
        'shelf_location',
        'status'
    )
    
    fieldsets = (
        ('Product Information', {
            'fields': (
                'product_name', 
                'batch_no', 
                'category', 
                'shelf_location',
                'original_quantity',
            )
        }),
        ('Stock Information', {
            'fields': (
                ('quantity', 'price'),
                'expiry_date', 
                'status', 
                'moved_to_pharmacy_date',
                'total_disposed',
                'remaining_quantity',
            )
        }),
    )
    
    readonly_fields = (
        'remaining_quantity', 
        'total_disposed',
        'expiry_status'
    )
    
    date_hierarchy = 'expiry_date'
    ordering = ('-created_at',)
    list_per_page = 50
    actions = ['mark_as_disposed', 'update_original_quantities']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('original_quantity',)
        return self.readonly_fields
    
    def expiry_status(self, obj):
        from django.utils import timezone
        if obj.expiry_date < timezone.now().date():
            return format_html(
                '<span style="color:red;font-weight:bold;">EXPIRED</span>'
            )
        elif (obj.expiry_date - timezone.now().date()).days <= 30:
            return format_html(
                '<span style="color:orange;font-weight:bold;">NEAR EXPIRY ({} days)</span>',
                (obj.expiry_date - timezone.now().date()).days
            )
        return format_html(
            '<span style="color:green;">OK ({} days)</span>',
            (obj.expiry_date - timezone.now().date()).days
        )
    expiry_status.short_description = 'Expiry Status'
    expiry_status.admin_order_field = 'expiry_date'
    
    def remaining_quantity(self, obj):
        return obj.remaining_quantity
    remaining_quantity.short_description = 'Remaining'
    remaining_quantity.admin_order_field = 'quantity'
    
    def mark_as_disposed(self, request, queryset):
        updated = queryset.update(status='disposed')
        self.message_user(
            request, 
            f"Successfully marked {updated} products as disposed"
        )
    mark_as_disposed.short_description = "Mark selected items as disposed"
    
    def update_original_quantities(self, request, queryset):
        for item in queryset:
            if item.original_quantity == 0:
                item.original_quantity = item.quantity
                item.save()
        self.message_user(
            request,
            f"Updated original quantities for {queryset.count()} items"
        )
    update_original_quantities.short_description = "Update original quantities"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only on create
            if obj.original_quantity == 0:
                obj.original_quantity = obj.quantity
        super().save_model(request, obj, form, change)
@admin.register(Disposal)
class DisposalAdmin(admin.ModelAdmin):
    list_display = (
        'inventory_link', 
        'disposal_date', 
        'method', 
        'quantity',
        'documented_by_link',
        'witnessed_by_link',
        'get_documentation'
    )
    
    list_filter = (
        'method', 
        'disposal_date', 
        'inventory__category'
    )
    
    search_fields = (
        'inventory__product_name', 
        'inventory__batch_no',
        'documented_by__name',
        'witnessed_by__name'
    )
    
    date_hierarchy = 'disposal_date'
    readonly_fields = ('created_at',)
    raw_id_fields = ('inventory', 'documented_by', 'witnessed_by')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('inventory', 'disposal_date')
        }),
        ('Disposal Details', {
            'fields': ('method', 'quantity', 'documentation', 'notes')
        }),
        ('Personnel', {
            'fields': ('documented_by', 'witnessed_by')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def inventory_link(self, obj):
        url = reverse('admin:inventory_inventory_change', args=[obj.inventory.id])
        return format_html(
            '<a href="{}">{} (Batch: {})</a>',
            url, 
            obj.inventory.product_name,
            obj.inventory.batch_no
        )
    inventory_link.short_description = 'Inventory Item'
    inventory_link.admin_order_field = 'inventory__product_name'

    def documented_by_link(self, obj):
        if obj.documented_by:
            url = reverse('admin:inventory_user_change', args=[obj.documented_by.id])
            return format_html(
                '<a href="{}">{}</a>', 
                url, 
                obj.documented_by.get_full_name() or obj.documented_by.username
            )
        return "-"
    documented_by_link.short_description = 'Documented By'
    documented_by_link.admin_order_field = 'documented_by'

    def witnessed_by_link(self, obj):
        if obj.witnessed_by:
            url = reverse('admin:inventory_user_change', args=[obj.witnessed_by.id])
            return format_html(
                '<a href="{}">{}</a>', 
                url, 
                obj.witnessed_by.get_full_name() or obj.witnessed_by.username
            )
        return "-"
    witnessed_by_link.short_description = 'Witnessed By'
    witnessed_by_link.admin_order_field = 'witnessed_by'

    def get_documentation(self, obj):
        if obj.documentation:
            return format_html(
                '<a href="{}" target="_blank">View Document</a>',
                obj.documentation.url
            )
        return "-"
    get_documentation.short_description = 'Documentation'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'inventory', 
            'documented_by', 
            'witnessed_by'
        )

class PharmacyLoanAdmin(admin.ModelAdmin):
    list_display = ('inventory', 'pharmacy_name', 'contact_person', 'loan_date', 'quantity_loaned', 
                    'quantity_returned', 'quantity_sold', 'status', 'return_date')
    list_filter = ('status', 'loan_date', 'return_date')
    search_fields = ('pharmacy_name', 'contact_person', 'inventory__product_name')  # Example of searching through related fields
    ordering = ('loan_date',)
    readonly_fields = ('loan_date',)  # Make the loan date read-only since it is auto-added
    fieldsets = (
        (None, {
            'fields': ('inventory', 'pharmacy_name', 'contact_person', 'contact_phone', 'quantity_loaned', 'notes')
        }),
        ('Dates', {
            'fields': ('loan_date', 'return_date')
        }),
        ('Status', {
            'fields': ('quantity_returned', 'quantity_sold', 'status')
        }),
    )

admin.site.register(PharmacyLoan, PharmacyLoanAdmin)
