import os
import django
import sys
from decimal import Decimal

# Add the project directory to sys.path
sys.path.append(r'c:\inetpub\wwwroot\FOLIUX')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Transaction, Instrument
from django.db.models import Sum

user = User.objects.get(id=4)

def calculate_invested_on(date_str):
    # This is a bit complex because we need to follow FIFO to know which lots remain
    txs = Transaction.objects.filter(user=user, date__lte=date_str).order_by('date', 'created_at')
    
    holdings = {} # symbol -> [lots]
    
    for t in txs:
        sym = t.instrument.symbol
        if t.transaction_type == 'BUY':
            if sym not in holdings: holdings[sym] = []
            holdings[sym].append({'qty': t.quantity, 'price': t.price})
        else:
            # SELL
            qty_to_sell = t.quantity
            if sym in holdings:
                while qty_to_sell > 0 and holdings[sym]:
                    lot = holdings[sym][0]
                    if lot['qty'] <= qty_to_sell:
                        qty_to_sell -= lot['qty']
                        holdings[sym].pop(0)
                    else:
                        lot['qty'] -= qty_to_sell
                        qty_to_sell = 0
    
    total_invested = Decimal('0')
    for sym, lots in holdings.items():
        for lot in lots:
            total_invested += Decimal(str(lot['qty'])) * lot['price']
    return total_invested

inv_23 = calculate_invested_on('2026-04-23')
inv_24 = calculate_invested_on('2026-04-24')

print(f"Invested on April 23: {inv_23}")
print(f"Invested on April 24: {inv_24}")
print(f"Change: {inv_24 - inv_23}")
