import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth.models import User

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.views import transaction_history

user = User.objects.filter(email='Jitendra.kar@gmail.com').first()
if user:
    rf = RequestFactory()
    request = rf.get('/transactions/')
    request.user = user
    response = transaction_history(request)
    content = response.content.decode('utf-8')
    
    import re
    dates = re.findall(r'data-date="([^"]*)"', content)
    print(f"Total dates found: {len(dates)}")
    for i, d in enumerate(dates[:15]):
        print(f"  Row {i}: '{d}'")
else:
    print("User not found.")
