import os
import sys
import django

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from collections import Counter
from django.contrib.auth.models import User
from core.models import Transaction

emails = ['Jitendra.kar@winmedicare.com', 'Jitendra.kar@gmail.com']

for email in emails:
    user = User.objects.filter(email__iexact=email).first()
    if user:
        txs = list(Transaction.objects.filter(user=user).select_related('instrument').order_by('-date', '-created_at'))
        rows_length = len(txs)
        
        if rows_length > 0:
            first_date = txs[0].date.strftime('%Y-%m-%d')
            visible_count = sum(1 for tx in txs if tx.date.strftime('%Y-%m-%d') == first_date)
        else:
            visible_count = 0
            
        print(f"User: {email}")
        print(f"  Rows Length: {rows_length}")
        print(f"  Visible Count (Collapsed): {visible_count}")
        print(f"  Condition (rows > visible): {rows_length > visible_count}")
    else:
        print(f"User {email} not found.")
