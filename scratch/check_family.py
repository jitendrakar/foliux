import os
import sys
import django

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import FamilyLink

email = 'Jitendra.kar@gmail.com'
user = User.objects.filter(email__iexact=email).first()

if user:
    links = FamilyLink.objects.filter(user=user)
    print(f"User {email} has {links.count()} family links.")
    for link in links:
        print(f"  Linked to: {link.family_user.email} (Verified: {link.is_verified})")
else:
    print(f"User {email} not found.")
