import os
import django
import sys
from decimal import Decimal

# Add the project directory to sys.path
sys.path.append(r'c:\inetpub\wwwroot\FOLIUX')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Portfolio, Transaction
from django.db.models import Sum, F

user_id = 4

# Pre-calculate transaction sums
t_sums = Transaction.objects.filter(
    user_id=user_id, 
    transaction_type='BUY', 
    remaining_quantity__gt=0
).values('instrument__symbol').annotate(
    total=Sum(F('remaining_quantity') * F('price'))
)
t_map = {item['instrument__symbol']: item['total'] for item in t_sums}

p_items = Portfolio.objects.filter(user_id=user_id).select_related('instrument')

print(f"{'Symbol':<15} | {'Portfolio Value':<15} | {'Transaction Sum':<15} | {'Diff':<15}")
print("-" * 65)

for p in p_items:
    sym = p.instrument.symbol
    p_val = p.quantity * p.avg_cost
    t_val = t_map.get(sym, Decimal('0'))
    
    diff = p_val - t_val
    if abs(diff) > 1:
        print(f"{sym:<15} | {p_val:<15.2f} | {t_val:<15.2f} | {diff:<15.2f}")
