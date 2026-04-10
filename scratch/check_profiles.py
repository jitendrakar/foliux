import os
import sys
import django

# Add the project root to sys.path
sys.path.append(r'c:\inetpub\wwwroot\NPITS')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Profile

# Check for a specific user or all users
for profile in Profile.objects.all():
    print(f"User: {profile.user.username}")
    if profile.profile_picture:
        print(f"  Picture Path: {profile.profile_picture.path}")
        print(f"  Picture URL: {profile.profile_picture.url}")
        print(f"  File Exists: {os.path.exists(profile.profile_picture.path)}")
    else:
        print("  No Picture")
