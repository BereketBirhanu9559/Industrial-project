# tasks.py (to be run periodically via cron)
from django.utils import timezone
from datetime import timedelta
from models import ReservedInventory

def cleanup_expired_reservations():
    """Release reservations older than 30 minutes"""
    expiry_time = timezone.now() - timedelta(minutes=30)
    expired_reservations = ReservedInventory.objects.filter(
        reservation_date__lte=expiry_time,
        is_active=True
    )
    
    expired_reservations.update(is_active=False)
    expired_reservations.delete()