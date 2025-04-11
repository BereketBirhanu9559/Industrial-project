# customer/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class Customer(AbstractUser):
    """Separate authentication model for customers"""
    # Remove unwanted fields from AbstractUser
    first_name = None
    last_name = None
    
    # Custom fields
    name = models.CharField(max_length=255)
    competency_document = models.FileField(upload_to='customer_docs/')
    phone_number = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        db_table = 'customer'  # Separate table
    
    def __str__(self):
        return f"{self.username} ({self.name})"