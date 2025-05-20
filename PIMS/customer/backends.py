from django.contrib.auth import get_user_model
from .models import Customer

class CustomerBackend:
    def authenticate(self, request, username=None, password=None):
        try:
            user = Customer.objects.get(username=username)
            if user.check_password(password):
                return user
        except Customer.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        try:
            return Customer.objects.get(pk=user_id)
        except Customer.DoesNotExist:
            return None