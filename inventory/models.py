from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

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
        primary_key=True  # Ensures one-to-one relationship
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='clerk'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update the user profile"""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Ensure profile exists for existing users
        UserProfile.objects.get_or_create(user=instance)
        instance.profile.save()

class Inventory(models.Model):
    product_name = models.CharField(max_length=255)
    batch_no = models.CharField(max_length=100)
    quantity = models.IntegerField()
    expiry_date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=255)
    shelf_location = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Shelf Location",
        help_text="Physical location of the product in storage"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} - Batch {self.batch_no}"

    class Meta:
        verbose_name_plural = "Inventory"
        ordering = ['product_name']