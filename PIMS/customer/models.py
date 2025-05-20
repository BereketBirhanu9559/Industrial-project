from django.conf import settings
from django.db import models
import uuid

class Customer(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    VERIFIED = 'verified'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (VERIFIED, 'Verified'),
    ]

    ROLE_CHOICES = [
        ('clerk', 'Clerk'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
        ('finance', 'Finance'),
        ('regulatory', 'Regulatory'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer",
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)
    temp_email = models.EmailField(unique=True)
    competency_document = models.FileField(upload_to='competency_docs/')
    phone_number = models.CharField(max_length=15, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        null=True,
        blank=True,
        default=None
    )

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.name} ({self.temp_email})"

from django.db import models
from inventory.models import Inventory  # Import Inventory from inventory app

class Sale(models.Model):
    product = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='customer_sales'  # Unique reverse accessor
    )
    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)
    customer_email = models.EmailField()
    status = models.CharField(max_length=20, default='completed')

    def __str__(self):
        return f"Sale {self.transaction_id} - {self.product.product_name}"