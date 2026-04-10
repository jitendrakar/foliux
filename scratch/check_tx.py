import os
import sys
import django

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Transaction

emails = ['Jitendra.kar@winmedicare.com', 'Jitendra.kar@gmail.com']

for email in emails:
    user = User.objects.filter(email__iexact=email).first()
    if user:
        tx_count = Transaction.objects.filter(user=user).count()
        dates = Transaction.objects.filter(user=user).values_list('date', flat=True).distinct().order_by('-date')
        print(f"User: {email} (ID: {user.id})")
        print(f"  Total Transactions: {tx_count}")
        print(f"  Distinct Dates: {list(dates)}")
    else:
        print(f"User with email {email} not found.")
