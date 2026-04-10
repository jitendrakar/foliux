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
    empty_symbols = re.findall(r'data-symbol=""', content)
    print(f"Empty symbols found: {len(empty_symbols)}")
    
    # Check for quotes in symbols
    bad_symbols = re.findall(r'data-symbol="[^"]*"[^"]*"', content)
    print(f"Badly quoted symbols: {len(bad_symbols)}")
else:
    print("User not found.")
