import os
import sys
import django

sys.path.append(r'c:\inetpub\wwwroot\NPITS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'investment_advisory.settings')
django.setup()

from core.models import Transaction

txs_with_no_inst = Transaction.objects.filter(instrument__isnull=True).count()
print(f"Transactions with no instrument: {txs_with_no_inst}")

# Check for transactions where instrument has no symbol
txs_with_no_symbol = Transaction.objects.filter(instrument__symbol__isnull=True).count()
print(f"Transactions with no symbol: {txs_with_no_symbol}")
