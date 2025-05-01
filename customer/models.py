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

    # ROLE_CHOICES for dropdown
    ROLE_CHOICES = [
        ('clerk', 'Clerk'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
        ('finance', 'Finance'),
        ('regulatory', 'Regulatory'),
    ]

    # Reference the custom user model using settings.AUTH_USER_MODEL
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer",
        null=True,  # Allow initially not linked
        blank=True
    )

    name = models.CharField(max_length=100)
    temp_email = models.EmailField(unique=True)
    competency_document = models.FileField(upload_to='competency_docs/')
    phone_number = models.CharField(max_length=15, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True)

    # Added fields
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Added role as a dropdown field
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        null=True,
        blank=True,
        default=None  # Default can be None if you want it to be unset initially
    )

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.name} ({self.temp_email})"
