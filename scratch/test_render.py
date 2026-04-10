import os
import sys
import django

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from core.views import transaction_history

emails = ['Jitendra.kar@winmedicare.com', 'Jitendra.kar@gmail.com']
rf = RequestFactory()

for email in emails:
    user = User.objects.filter(email__iexact=email).first()
    if user:
        request = rf.get('/transactions/')
        request.user = user
        response = transaction_history(request)
        content = response.content.decode('utf-8')
        
        # Check for the button
        has_btn = 'id="toggleTxBtn"' in content
        # Check for rows
        row_count = content.count('class="transaction-row"')
        
        print(f"User: {email}")
        print(f"  Button ID present: {has_btn}")
        print(f"  Transaction rows in HTML: {row_count}")
    else:
        print(f"User {email} not found.")
