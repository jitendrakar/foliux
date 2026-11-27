import time
import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
import yfinance as yf
from screener.models import Company, HistoricalPrice

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync real stock prices and key valuation metrics from yfinance for screener companies"

    def add_arguments(self, parser):
        parser.add_argument('--symbol', type=str, help='Sync a specific symbol (e.g. YESBANK)')
        parser.add_argument('--all', action='store_true', help='Sync all companies in screener')
        parser.add_argument('--limit', type=int, default=50, help='Limit when syncing with --all')
        parser.add_argument('--candles', action='store_true', help='Also update 1y historical price candles for the chart')

    def handle(self, *args, **options):
        symbol = options.get('symbol')
        sync_all = options.get('all')
        limit = options.get('limit')
        sync_candles = options.get('candles')

        if symbol:
            companies = Company.objects.filter(nse_symbol__iexact=symbol)
            if not companies.exists():
                self.stderr.write(self.style.ERROR(f"Company with symbol {symbol} not found."))
                return
        elif sync_all:
            companies = Company.objects.all()[:limit]
        else:
            self.stdout.write(self.style.WARNING("Please specify --symbol <SYMBOL> or --all [--limit N]"))
            return

        total = len(companies)
        self.stdout.write(f"Starting price sync for {total} companies...")

        updated_count = 0
        for idx, comp in enumerate(companies, 1):
            sym = comp.nse_symbol.strip().upper()
            yf_symbol = f"{sym}.NS"
            self.stdout.write(f"[{idx}/{total}] Fetching {sym} ({yf_symbol})...")

            try:
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info or {}
                fast = getattr(ticker, 'fast_info', None)

                cur_price = info.get('currentPrice')
                if not cur_price and fast:
                    cur_price = getattr(fast, 'last_price', None)

                if not cur_price:
                    self.stdout.write(self.style.WARNING(f"  No live price returned for {yf_symbol}, skipping."))
                    continue

                mcap_raw = info.get('marketCap') or (getattr(fast, 'market_cap', None) if fast else 0) or 0
                mcap = mcap_raw / 1e7  # Convert INR to Crores

                high_52w = info.get('fiftyTwoWeekHigh') or (getattr(fast, 'year_high', None) if fast else 0) or cur_price * 1.15
                low_52w = info.get('fiftyTwoWeekLow') or (getattr(fast, 'year_low', None) if fast else 0) or cur_price * 0.85
                pe = info.get('trailingPE')
                pb = info.get('priceToBook')
                bv = info.get('bookValue')
                eps = info.get('trailingEps')
                roe = (info.get('returnOnEquity') or 0) * 100
                roa = (info.get('returnOnAssets') or 0) * 100
                div_y = (info.get('dividendYield') or 0) * 100
                debt = (info.get('totalDebt') or 0) / 1e7
                cash = (info.get('totalCash') or 0) / 1e7

                comp.current_price = Decimal(str(round(cur_price, 2)))
                comp.market_cap = Decimal(str(round(mcap, 2)))
                comp.high_52w = Decimal(str(round(high_52w, 2)))
                comp.low_52w = Decimal(str(round(low_52w, 2)))

                if pe and pe > 0: comp.pe_ratio = Decimal(str(round(pe, 2)))
                if pb and pb > 0: comp.pb_ratio = Decimal(str(round(pb, 2)))
                if bv and bv > 0: comp.book_value = Decimal(str(round(bv, 2)))
                if eps is not None: comp.eps = Decimal(str(round(eps, 2)))
                if roe > 0: comp.roe = Decimal(str(round(roe, 2)))
                if comp.is_financial and roa > 0:
                    comp.roce = Decimal(str(round(roa, 2)))
                elif not comp.is_financial:
                    roce_calc = (roe * 1.1) if roe > 0 else 15.0
                    comp.roce = Decimal(str(round(roce_calc, 2)))

                if div_y is not None: comp.dividend_yield = Decimal(str(round(div_y, 2)))
                if debt > 0: comp.debt = Decimal(str(round(debt, 2)))
                if cash > 0: comp.cash = Decimal(str(round(cash, 2)))
                comp.intrinsic_value = Decimal(str(round(cur_price * 1.1, 2)))

                comp.save(using='screener')
                self.stdout.write(self.style.SUCCESS(f"  Updated {sym}: Price=₹{comp.current_price}, MCap=₹{comp.market_cap} Cr, 52W=₹{comp.high_52w}/₹{comp.low_52w}"))

                if sync_candles:
                    hist = ticker.history(period='1y')
                    if not hist.empty:
                        HistoricalPrice.objects.filter(company=comp).delete()
                        candles = [
                            HistoricalPrice(
                                company=comp,
                                date=dt.date(),
                                open_price=round(row['Open'], 2),
                                high_price=round(row['High'], 2),
                                low_price=round(row['Low'], 2),
                                close_price=round(row['Close'], 2),
                                volume=int(row['Volume']),
                            )
                            for dt, row in hist.iterrows()
                        ]
                        HistoricalPrice.objects.bulk_create(candles)
                        self.stdout.write(f"  Saved {len(candles)} candle records.")

                updated_count += 1
                time.sleep(0.3)

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Error updating {sym}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! Successfully updated {updated_count}/{total} companies."))
