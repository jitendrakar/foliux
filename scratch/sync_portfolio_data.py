import os
import django
import sys
from decimal import Decimal

# Add the project directory to sys.path
sys.path.append(r'c:\inetpub\wwwroot\FOLIUX')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Portfolio, Transaction, Instrument
from django.db.models import Sum, F
from django.contrib.auth.models import User

def sync_user_portfolio(user):
    print(f"Syncing portfolio for user: {user.username}")
    
    # 1. Get all active BUY lots
    active_lots = Transaction.objects.filter(
        user=user, 
        transaction_type='BUY', 
        remaining_quantity__gt=0
    ).values('instrument').annotate(
        total_qty=Sum('remaining_quantity'),
        total_cost=Sum(F('remaining_quantity') * F('price'))
    )
    
    active_instrument_ids = set()
    
    for lot in active_lots:
        instr_id = lot['instrument']
        total_qty = lot['total_qty']
        avg_cost = lot['total_cost'] / total_qty if total_qty > 0 else 0
        
        active_instrument_ids.add(instr_id)
        
        # Update or create portfolio item
        portfolio, created = Portfolio.objects.get_or_create(
            user=user,
            instrument_id=instr_id,
            defaults={'quantity': total_qty, 'avg_cost': avg_cost}
        )
        
        if not created:
            if portfolio.quantity != total_qty or abs(portfolio.avg_cost - avg_cost) > Decimal('0.01'):
                print(f"  Updating {portfolio.instrument.symbol}: Qty {portfolio.quantity}->{total_qty}, Avg {portfolio.avg_cost}->{avg_cost}")
                portfolio.quantity = total_qty
                portfolio.avg_cost = avg_cost
                portfolio.save()
        else:
            print(f"  Created missing portfolio entry for {portfolio.instrument.symbol}")

    # 2. Remove items that have no active lots
    stale_items = Portfolio.objects.filter(user=user).exclude(instrument_id__in=active_instrument_ids)
    for item in stale_items:
        print(f"  Removing phantom portfolio entry for {item.instrument.symbol} (Qty: {item.quantity})")
        item.delete()

# Run for user ID 4
user = User.objects.get(id=4)
sync_user_portfolio(user)

# Also run for the other user mentioned in logs if needed, but ID 4 is the main one.
print("Sync complete.")
