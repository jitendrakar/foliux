from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Profile

User = get_user_model()

import logging
logger = logging.getLogger(__name__)

class EmailOrMobileBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('username')
        
        if not username:
            return None

        logger.debug(f"Attempting authenticate for: {username}")
        
        try:
            # 1. Try exact matches on username and email (FAST)
            user = User.objects.filter(
                Q(username__iexact=username) | 
                Q(email__iexact=username)
            ).first()

            # 2. If not found, check if it's a mobile number
            # Since profile.mobile_number is an EncryptedCharField, we cannot filter by it in the DB.
            # We must iterate and check in memory. 
            # Note: This is acceptable for small to medium user bases.
            if not user:
                # Basic check to see if it might be a mobile number (numeric)
                cleaned_username = str(username).replace(" ", "").replace("-", "").replace("+", "")
                if cleaned_username.isdigit():
                    profiles = Profile.objects.select_related('user').all()
                    for profile in profiles:
                        # Accessing .mobile_number decrypts it automatically
                        if profile.mobile_number == username or profile.mobile_number == cleaned_username:
                            user = profile.user
                            break
            
        except Exception as e:
            logger.error(f"Authentication backend error: {e}")
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
