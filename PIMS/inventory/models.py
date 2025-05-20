from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from django.db.models import Sum  
from django.core.exceptions import ValidationError

class User(AbstractUser):
    name = models.CharField(max_length=255, verbose_name="Full Name")

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='parking_user_groups',
        blank=True,
        verbose_name='groups'
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='parking_user_permissions',
        blank=True,
        verbose_name='user permissions'
    )

    def __str__(self):
        return self.username

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('clerk', 'Clerk'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
        ('finance', 'Finance'),
        ('regulatory', 'Regulatory'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        primary_key=True
    )
    # Set role to null=True to make it nullable initially
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=None,  # This ensures that role is nullable and defaults to None
        null=True,  # Allow null values
        blank=True  # Allow the field to be blank in forms
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display() if self.role else 'No Role'}"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Automatically create or update user profile when a User is saved."""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)
        instance.profile.save()


class Inventory(models.Model):
    CATEGORY_CHOICES = [
        ('antibiotics', 'Antibiotics'),
        ('pain_relievers', 'Pain Relievers (Analgesics)'),
        ('anti_inflammatory', 'Antipyretics and Anti-inflammatory Drugs'),
        ('gastrointestinal', 'Antacids and Gastrointestinal Medicines'),
        ('vitamins', 'Vitamins and Supplements'),
        ('antidiabetics', 'Antidiabetics'),
        ('cardiovascular', 'Cardiovascular Medicines'),
        ('respiratory', 'Respiratory Medicines (Asthma, COPD)'),
        ('antimalarials', 'Antimalarials'),
        ('cough_cold', 'Cough and Cold Preparations'),
    ]

    product_name = models.CharField(max_length=255)
    batch_no = models.CharField(max_length=100)
    quantity = models.IntegerField()
    reserved_quantity = models.IntegerField(default=0, help_text="Quantity reserved during payment")
    expiry_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='antibiotics',
        verbose_name="Category"
    )
    shelf_location = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Shelf Location",
        help_text="Physical location of the product in storage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('expired', 'Expired'),
        ('disposed', 'Disposed'),
        ('quarantined', 'Quarantined'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    moved_to_pharmacy_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Moved to Pharmacy Date",
        help_text="Date when product was moved to pharmacy section"
    )
    original_quantity = models.IntegerField(
        default=0,
        verbose_name="Original Quantity",
        help_text="Initial quantity when product was added"
    )
    total_disposed = models.IntegerField(
        default=0,
        verbose_name="Total Disposed",
        help_text="Sum of all disposed quantities"
    )

    @property
    def loaned_quantity(self):
        """Total quantity currently on loan to pharmacies"""
        return PharmacyLoan.objects.filter(
            inventory=self,
            status='on_loan'
        ).aggregate(total=Sum('quantity_loaned'))['total'] or 0

    @property
    def returned_quantity(self):
        """Total quantity returned from pharmacies (available for disposal)"""
        return PharmacyLoan.objects.filter(inventory=self).aggregate(
            total=Sum('quantity_returned')
        )['total'] or 0

    @property
    def remaining_pre_loan_quantity(self):
        """
        Quantity remaining before loaning to pharmacies (nearly expiry stage).
        This is the original quantity minus what's been loaned out.
        """
        return max(0, self.quantity - self.loaned_quantity)

    @property
    def remaining_post_return_quantity(self):
        """
        Quantity remaining after returns from pharmacies (expiry stage).
        This is the returned quantity minus what's been disposed.
        """
        return max(0, self.returned_quantity - self.total_disposed)

    NEAR_EXPIRY_THRESHOLD = 180  # 6 months in days

    @classmethod
    def get_near_expiry_products(cls):
        """Returns queryset of products with <= 6 months to expiry"""
        threshold_date = timezone.now().date() + timedelta(days=cls.NEAR_EXPIRY_THRESHOLD)
        return cls.objects.filter(
            expiry_date__range=[timezone.now().date(), threshold_date],
            status='available'
        ).order_by('expiry_date')

    @property
    def is_near_expiry(self):
        return (self.expiry_date - timezone.now().date()).days <= self.NEAR_EXPIRY_THRESHOLD

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days

    def reserve_quantity(self, quantity):
        """Reserve a quantity for payment processing"""
        if quantity <= (self.quantity - self.reserved_quantity):
            self.reserved_quantity += quantity
            self.save()
            return True
        return False

    def release_reserved_quantity(self, quantity):
        """Release reserved quantity back to inventory"""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
        self.save()

    def deduct_quantity(self, quantity):
        """Deduct quantity from inventory after successful payment"""
        if quantity <= self.quantity:
            self.quantity -= quantity
            self.reserved_quantity = max(0, self.reserved_quantity - quantity)
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.product_name} - Batch {self.batch_no}"

    class Meta:
        verbose_name_plural = "Inventories"

class PharmacyLoan(models.Model):
    STATUS_CHOICES = [
        ('on_loan', 'On Loan to Pharmacy'),
        ('returned', 'Returned to Warehouse'),
        ('sold', 'Sold by Pharmacy'),
    ]
    
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    pharmacy_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=20)
    loan_date = models.DateField(auto_now_add=True)
    return_date = models.DateField(null=True, blank=True)
    quantity_loaned = models.IntegerField()
    quantity_returned = models.IntegerField(default=0)
    quantity_sold = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on_loan')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.inventory} to {self.pharmacy_name} ({self.status})"
class Disposal(models.Model):
    METHOD_CHOICES = [
        ('incineration', 'Incineration'),
        ('landfill', 'Sanitary Landfill'),
        ('return', 'Returned to Manufacturer'),
        ('other', 'Other Method'),
    ]
    
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    disposal_date = models.DateField(default=timezone.now)
    method = models.CharField(max_length=50, choices=METHOD_CHOICES)
    quantity = models.IntegerField()
    witnessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='disposals_witnessed'
    )
    documented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='disposals_documented'
    )
    documentation = models.FileField(
        upload_to='disposals/%Y/%m/%d/',
        blank=True,
        null=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.pk:
            inventory = self.inventory
            new_total_disposed = inventory.total_disposed + self.quantity

            # Cap disposed quantity to not exceed returned
            if new_total_disposed >= inventory.returned_quantity:
                inventory.total_disposed = inventory.returned_quantity
                inventory.status = 'disposed'
            else:
                inventory.total_disposed = new_total_disposed

            inventory.save()
        
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Disposal of {self.inventory} on {self.disposal_date}"
    

class Transaction(models.Model):
    tx_ref = models.CharField(max_length=50, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField()
    status = models.CharField(max_length=20, default='pending')
    cart = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_cart(self, cart):
        self.cart = cart
        self.save()

    def get_cart(self):
        return self.cart

    def __str__(self):
        return f"Transaction {self.tx_ref} ({self.status})"


class Sale(models.Model):
    product = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='sales')
    customer_email = models.EmailField()
    status = models.CharField(max_length=20, default='completed')
    sale_date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if self.total_amount <= 0:
            raise ValidationError("Total amount must be positive.")

    def __str__(self):
        return f"Sale of {self.quantity} {self.product.product_name} on {self.sale_date}"