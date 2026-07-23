from django.core.management.base import BaseCommand
from core.models import Instrument, StrategyStock, Portfolio, Transaction, PnLStatement, Watchlist, HiddenSignal
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Renames AXISVALUE symbol to VALUEAXIS across all models and clears cache.'

    def handle(self, *args, **options):
        self.stdout.write("Renaming AXISVALUE to VALUEAXIS in database...")
        
        # Update StrategyStock
        s_count = StrategyStock.objects.filter(symbol__iexact='AXISVALUE').update(symbol='VALUEAXIS')
        
        # Update Instrument
        i_count = Instrument.objects.filter(symbol__iexact='AXISVALUE').update(symbol='VALUEAXIS')
        
        # Update Portfolios if instrument wasn't linked by FK string
        p_count = Portfolio.objects.filter(instrument__symbol__iexact='AXISVALUE').count()
        
        # Update Watchlist
        w_count = Watchlist.objects.filter(instrument__symbol__iexact='AXISVALUE').count()

        # Clear Django Cache
        cache.clear()
        
        self.stdout.write(self.style.SUCCESS(
            f"Successfully renamed AXISVALUE to VALUEAXIS:\n"
            f"  - StrategyStock records updated: {s_count}\n"
            f"  - Instrument records updated: {i_count}\n"
            f"  - Associated Portfolios: {p_count}\n"
            f"  - Associated Watchlists: {w_count}\n"
            f"  - Django cache cleared."
        ))
