from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class RoleBasedAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, role=None, **kwargs):
        try:
            # First try to authenticate superusers without role check
            user = User.objects.get(username=username)
            if user.is_superuser:
                if user.check_password(password):
                    return user
                return None
            
            # For regular users, check role
            user = User.objects.get(username=username, role=role)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None