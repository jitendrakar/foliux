import os
import sys
import django
from collections import Counter

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Transaction

email = 'Jitendra.kar@gmail.com'
user = User.objects.filter(email__iexact=email).first()

if user:
    txs = Transaction.objects.filter(user=user).order_by('-date', '-created_at')
    counts = Counter(tx.date for tx in txs)
    print(f"User {email} Transaction Counts per Date:")
    for date, count in sorted(counts.items(), key=lambda x: x[0], reverse=True):
        print(f"  {date}: {count}")
else:
    print(f"User {email} not found.")
