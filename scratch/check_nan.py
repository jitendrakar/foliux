import os
import sys
import django
import math

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import PortfolioValueHistory

email = 'Jitendra.kar@gmail.com'
user = User.objects.filter(email__iexact=email).first()

if user:
    history = PortfolioValueHistory.objects.filter(user=user)
    print(f"Checking {history.count()} history records for {email}...")
    bad_records = 0
    for h in history:
        if math.isnan(float(h.stock_invested)) or math.isinf(float(h.stock_invested)):
            print(f"  Bad stock_invested on {h.date}: {h.stock_invested}")
            bad_records += 1
        if math.isnan(float(h.stock_current)) or math.isinf(float(h.stock_current)):
            print(f"  Bad stock_current on {h.date}: {h.stock_current}")
            bad_records += 1
        if h.nifty_price and (math.isnan(float(h.nifty_price)) or math.isinf(float(h.nifty_price))):
            print(f"  Bad nifty_price on {h.date}: {h.nifty_price}")
            bad_records += 1
    
    if bad_records == 0:
        print("  All records look clean.")
    else:
        print(f"  Found {bad_records} bad records.")
else:
    print(f"User {email} not found.")
