import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Profile

# Update profiles where brokerage is the old default 0.02 or is None
profiles_to_update = Profile.objects.filter(
    equity_brokerage_pct__in=[Decimal('0.0200'), None]
) | Profile.objects.filter(
    intraday_brokerage_pct__in=[Decimal('0.0200'), None]
)

count = 0
for profile in profiles_to_update:
    if profile.equity_brokerage_pct == Decimal('0.0200') or profile.equity_brokerage_pct is None:
        profile.equity_brokerage_pct = Decimal('0.2000')
    if profile.intraday_brokerage_pct == Decimal('0.0200') or profile.intraday_brokerage_pct is None:
        profile.intraday_brokerage_pct = Decimal('0.2000')
    profile.save()
    count += 1

print(f"Updated {count} profiles to use the new 0.2% default.")
