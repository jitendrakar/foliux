import os
import sys
import django

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Transaction
from django.contrib.auth.models import User

user = User.objects.filter(email='Jitendra.kar@gmail.com').first()
if user:
    latest_txs = Transaction.objects.filter(user=user).order_by('-date', '-created_at')[:20]
    for tx in latest_txs:
        print(f"Date: {tx.date} (Type: {type(tx.date)}) | Symbol: {tx.instrument.symbol}")
else:
    print("User not found.")
