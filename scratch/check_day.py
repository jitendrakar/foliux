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
    txs = Transaction.objects.filter(user=user, date='2026-04-09').order_by('-created_at')
    print(f"Total for 2026-04-09: {txs.count()}")
    for tx in txs:
        print(f"  [{tx.transaction_type}] {tx.instrument.symbol} | Qty: {tx.quantity} | Price: {tx.price}")
else:
    print("User not found.")
