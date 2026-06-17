import pandas as pd
import requests
import io
import logging
from django.core.cache import cache
import yfinance as yf
from django.conf import settings

logger = logging.getLogger(__name__)

from django.utils import timezone
import threading
from django import db
import math
from decimal import Decimal
from django.db.models import Sum, Max
from django.db.models.functions import Upper
from django.db import transaction
from core.models import Instrument

def clean_float(val, default=0.0):
    """Robustly convert a value to float, handling commas and currency symbols."""
    if val is None or val == '' or (isinstance(val, float) and math.isnan(val)):
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Remove commas, currency symbols, and whitespace
        clean_val = val.replace(',', '').replace('₹', '').replace('$', '').strip()
        try:
            return float(clean_val)
        except ValueError:
            return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def resolve_instrument(symbol_or_name):
    """
    Tries to resolve an Instrument object from a symbol or name.
    1. Exact symbol match
    2. Exact name match
    3. Symbol match without common suffixes (-GB, -BE, -EQ, etc.)
    """
    if not symbol_or_name:
        return None
        
    clean_val = str(symbol_or_name).strip().upper()
    
    # 1. Exact Symbol Match
    inst = Instrument.objects.filter(symbol__iexact=clean_val, is_verified=True).first()
    if inst:
        return inst
        
    # 2. Exact Name Match
    inst = Instrument.objects.filter(name__iexact=clean_val, is_verified=True).first()
    if inst:
        return inst
        
    # 3. Handle suffixes (e.g., SGBMAR31IV-GB -> SGBMAR31IV)
    # Common suffixes in Indian markets
    suffixes = ['-GB', '-BE', '-EQ', '.NS', '.BO']
    for suffix in suffixes:
        if clean_val.endswith(suffix):
            base = clean_val[:-len(suffix)]
            inst = Instrument.objects.filter(symbol__iexact=base, is_verified=True).first()
            if inst:
                return inst
            inst = Instrument.objects.filter(name__iexact=base, is_verified=True).first()
            if inst:
                return inst
                
    return None

def perform_sync():
    """Execute the synchronization logic for market tickers and instruments."""
    from core.models import MarketTicker, Instrument, Portfolio
    logger.info("Starting background sync process...")
    
    # 1. Sync Market Ticker Data
    market_url = f"https://docs.google.com/spreadsheets/d/{settings.MASTER_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=market"
    try:
        response = requests.get(market_url, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        
        seen_tickers = set()
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    name = str(row.iloc[0]).strip()
                    price_val = row.iloc[1]
                    change = row.iloc[2] if len(row) > 2 else 0
                    
                    if pd.notna(name) and pd.notna(price_val):
                        if isinstance(price_val, str) and price_val.lower() == 'nan':
                            continue
                        try:
                            price = clean_float(price_val, default=None)
                            if price is None:
                                continue
                                
                            try:
                                change_val = clean_float(change, default=0.0)
                            except Exception:
                                change_val = 0
                            
                            prev_price = price - change_val
                            pct_val = (change_val / prev_price * 100) if prev_price else 0
                            
                            MarketTicker.objects.update_or_create(
                                name=name,
                                defaults={'price': price, 'change': change_val, 'percent_change': pct_val}
                            )
                            seen_tickers.add(name)
                        except (ValueError, TypeError):
                            continue
                except Exception as e:
                    logger.error(f"Error processing market ticker row: {e}")
        
        # 1a. Explicitly sync major indices via yfinance (more reliable than sheet/info)
        major_indices = {
            'NIFTY 50': '^NSEI',
            'SENSEX': '^BSESN',
            'NIFTY BANK': '^NSEBANK',
            'GOLD': 'GC=F',
            'SILVER': 'SI=F'
        }
        
        for name, sym in major_indices.items():
            seen_tickers.add(name)
            try:
                ticker = yf.Ticker(sym)
                # Use fast_info for real-time price and previous close, much more reliable than history during market hours
                try:
                    cp = float(ticker.fast_info['last_price'])
                    pc = float(ticker.fast_info['previous_close'])
                    if cp and pc:
                        change_val = round(cp - pc, 2)
                        pct = round((change_val / pc) * 100, 2)
                        MarketTicker.objects.update_or_create(
                            name=name,
                            defaults={'price': round(cp, 2), 'change': change_val, 'percent_change': pct}
                        )
                        continue # Success with fast_info
                except Exception:
                    pass

                # Fallback to history if fast_info fails
                hist = ticker.history(period='5d')
                if not hist.empty:
                    cp = float(hist['Close'].iloc[-1])
                    pc = float(hist['Close'].iloc[-2]) if len(hist) > 1 else cp
                    change_val = round(cp - pc, 2)
                    pct = round((change_val / pc) * 100, 2) if pc else 0
                    
                    MarketTicker.objects.update_or_create(
                        name=name,
                        defaults={'price': round(cp, 2), 'change': change_val, 'percent_change': pct}
                    )
            except Exception as ex:
                logger.error(f"Error fetching live index override for {name}: {ex}")

        # Delete tickers not in the current sheet OR major indices
        if seen_tickers:
            deleted_count, _ = MarketTicker.objects.exclude(name__in=seen_tickers).delete()
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} stale market tickers.")
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")

    # 2. Sync Instrument LTP Data (from 'n2g' sheet)
    ltp_url = f"https://docs.google.com/spreadsheets/d/{settings.MASTER_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=n2g"
    try:
        response = requests.get(ltp_url, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text), skiprows=1)
        
        ltp_map = {}
        for _, row in df.iterrows():
            try:
                symbol_val = row.iloc[2]
                if pd.isna(symbol_val): continue
                symbol = str(symbol_val).strip().upper()
                if not symbol or symbol == 'NAN': continue
                
                ltp_val = row.iloc[4]
                if pd.isna(ltp_val): continue
                ltp = clean_float(ltp_val, default=None)
                if ltp is None or ltp == 0:
                    continue

                # Priority Day Change and % from Sheet (Index 5 and 6)
                change_val = clean_float(row.iloc[5], default=0.0) if len(row) > 5 else 0.0
                pct_val = clean_float(row.iloc[6], default=0.0) if len(row) > 6 else 0.0

                # Special Case: Update NIFTY 50 if found in Instrument Sheet
                if "NIFTY_50" in symbol or "NIFTY 50" in symbol:
                    MarketTicker.objects.update_or_create(
                        name='NIFTY 50',
                        defaults={'price': ltp, 'change': change_val, 'percent_change': pct_val}
                    )
                
                pe_val = clean_float(row.iloc[9], default=None) if len(row) > 9 else None
                lh_diff_val = clean_float(row.iloc[10], default=None) if len(row) > 10 else None
                high_52w_val = clean_float(row.iloc[8], default=None) if len(row) > 8 else None

                if ltp and ltp > 0:
                    # Map: (ltp, change, pe, lh_diff, h52, pct)
                    ltp_map[symbol] = (ltp, change_val, pe_val, lh_diff_val, high_52w_val, pct_val)
            except (ValueError, TypeError, IndexError):
                continue
        
        # Override with real 52W High from yfinance for verified instruments
        try:
            from core.models import Instrument
            verified_symbols = list(Instrument.objects.filter(is_verified=True).values_list('symbol', flat=True))
            if verified_symbols:
                # Prepare symbols for yfinance (append .NS if needed)
                yf_symbols = []
                for s in verified_symbols:
                    if not any(x in s for x in ['^', '.', '=F']):
                        yf_symbols.append(f"{s}.NS")
                    else:
                        yf_symbols.append(s)
                
                # Fetch 1y data in batches to get max High (52W High)
                # Batching for reliability
                batch_size = 50
                for i in range(0, len(yf_symbols), batch_size):
                    batch = yf_symbols[i:i+batch_size]
                    tickers = yf.Tickers(" ".join(batch))
                    hist = tickers.history(period='1y', interval='1d')
                    if not hist.empty and 'High' in hist:
                        highs = hist['High'].max()
                        for s_full in batch:
                            s_clean = s_full.replace('.NS', '').upper()
                            if s_full in highs and not pd.isna(highs[s_full]):
                                h52 = float(highs[s_full])
                                if s_clean in ltp_map:
                                    # Update ltp_map if it exists (index 4 is high_52w)
                                    m = list(ltp_map[s_clean])
                                    m[4] = h52
                                    ltp_map[s_clean] = tuple(m)
                                else:
                                    # Placeholder ltp/change if not in sheet map - use existing LTP if available
                                    inst_obj = Instrument.objects.filter(symbol=s_clean).first()
                                    existing_ltp = float(inst_obj.last_price) if inst_obj else 0
                                    # Map: (ltp, change, pe, lh_diff, h52, pct)
                                    ltp_map[s_clean] = (existing_ltp, 0, None, None, h52, 0)
        except Exception as ey:
            logger.error(f"Error fetching real 52W High via yfinance: {ey}")

        if ltp_map:
            with transaction.atomic():
                # Update Instruments
                instruments = Instrument.objects.filter(symbol__in=ltp_map.keys())
                for inst in instruments:
                    m_data = ltp_map[inst.symbol]
                    ltp = m_data[0]
                    change = m_data[1]
                    pe = m_data[2]
                    lh_diff = m_data[3]
                    h52 = m_data[4]
                    pct = m_data[5] if len(m_data) > 5 else 0
                    
                    inst.last_price = ltp
                    inst.price_change = change
                    # Prioritize exact previous close calculation if change is from sheet
                    inst.previous_close = ltp - change
                    inst.pe_ratio = pe
                    inst.diff_from_lh_pct = lh_diff
                    inst.high_52w = h52
                    inst.last_updated = timezone.now()
                    inst.save(update_fields=['last_price', 'price_change', 'previous_close', 'pe_ratio', 'diff_from_lh_pct', 'high_52w', 'last_updated'])
                
                # Update Portfolios
                portfolios = Portfolio.objects.all().select_related('instrument')
                for p in portfolios:
                    symbol = p.instrument.symbol.upper()
                    if symbol in ltp_map:
                        ltp = ltp_map[symbol][0]
                        if float(p.ltp) != float(ltp):
                            p.ltp = ltp
                            p.save(update_fields=['ltp'])
    except Exception as e:
        logger.error(f"Error fetching instrument data: {e}")
    except Exception as e:
        logger.error(f"Error fetching instrument data: {e}")

    # 3. Sync Strategy Stocks
    STRATEGY_SHEET_TABS = {
        'flexi': ('FlexiMultiInvest', 'Flexi Multi Invest'),
        'quant': ('NiftyQuant', 'Nifty Quant'),
        'pyramid': ('Pyramiding', 'Pyramiding'),
        'growth': ('ReinvestX', 'Reinvest X'),
    }
    # Using settings.MASTER_SHEET_ID instead of hardcoded SHEET_ID
    
    from core.models import Strategy, StrategyStock
    for strategy_key, (tab_name, display_name) in STRATEGY_SHEET_TABS.items():
        url = f"https://docs.google.com/spreadsheets/d/{settings.MASTER_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={tab_name}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            strategy, _ = Strategy.objects.get_or_create(
                name=strategy_key,
                defaults={'display_name': display_name}
            )
            
            # Clear existing stocks for this strategy
            StrategyStock.objects.filter(strategy=strategy).delete()
            
            stocks_to_create = []
            order = 0
            for line in response.text.splitlines():
                parts = line.split(',')
                if not parts: continue
                symbol = parts[0].strip().strip('"').strip().upper()
                if symbol and symbol != 'NAN' and symbol != 'SYMBOL':
                    stocks_to_create.append(StrategyStock(
                        strategy=strategy,
                        symbol=symbol,
                        order=order
                    ))
                    order += 1
            
            if stocks_to_create:
                StrategyStock.objects.bulk_create(stocks_to_create)
                logger.info(f"Synced {len(stocks_to_create)} stocks for strategy: {strategy_key}")
                
        except Exception as e:
            logger.error(f"Error syncing {tab_name} strategy stocks: {e}")
    
    logger.info("Starting background sync process...")
    
    # After sync is done, record history for all users
    try:
        from django.contrib.auth.models import User
        users = User.objects.all()
        for user in users:
            record_portfolio_value_history(user)
        logger.info("Recorded portfolio history for all users.")
    except Exception as e:
        logger.error(f"Error recording portfolio history for all users: {e}")

    logger.info("Sync process completed.")

def sync_mutual_funds_from_sheet():
    """Sync Mutual Fund NAVs from Google Sheet with yfinance fallback."""
    from core.models import MutualFund
    from decimal import Decimal
    import re
    
    sheet_url = "https://docs.google.com/spreadsheets/d/12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4/export?format=csv&gid=956419944"
    
    try:
        response = requests.get(sheet_url, timeout=15)
        response.raise_for_status()
        
        # Read the sheet (CSV). Assuming headerless based on content view.
        df = pd.read_csv(io.StringIO(response.text), header=None)
        
        count = 0
        for _, row in df.iterrows():
            try:
                name_val = row.iloc[0]
                if pd.isna(name_val): continue
                raw_name = str(name_val).strip()
                if not raw_name or raw_name == 'nan': continue
                
                # Extract clean name (often contains emails/notes after / or ;)
                clean_name = re.split(r'[/;]', raw_name)[0].strip()
                # Remove technical codes often appended in parentheses like (MUTF_IN:...)
                clean_name = re.sub(r'\s*[\(\[].*?MUTF_IN:.*?[\)\]]', '', clean_name).strip()
                
                # Column B is Symbol or ID
                symbol = str(row.iloc[1]).strip() if len(row) > 1 else raw_name
                
                # Column C is NAV Price
                sheet_nav = clean_float(row.iloc[2], default=0.0) if len(row) > 2 else 0
                
                # Column D is % Changes
                sheet_change = clean_float(row.iloc[3], default=0.0) if len(row) > 3 else 0

                target_nav = sheet_nav
                
                # yfinance logic: Try if symbol looks like a ticker and is not an internal ID
                if symbol and 'MUTF_IN:' not in symbol:
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        yf_nav = info.get('regularMarketPrice') or info.get('navPrice')
                        if yf_nav:
                            target_nav = float(yf_nav)
                    except Exception:
                        pass
                
                # Update or create MutualFund record
                fund, created = MutualFund.objects.get_or_create(symbol=symbol)
                
                # Store previous nav for day change calculation
                if not created:
                    fund.prev_nav = fund.nav
                else:
                    # For new records, try to estimate previous NAV from sheet's percentage change if available
                    if sheet_change != 0:
                        # sheet_change is usually a percentage (e.g., 1.5 for 1.5%)
                        prev_est = float(target_nav) / (1 + (sheet_change / 100))
                        fund.prev_nav = Decimal(str(round(prev_est, 4)))
                    else:
                        fund.prev_nav = Decimal(str(target_nav))
                
                fund.name = clean_name
                fund.nav = Decimal(str(target_nav))
                fund.save()
                count += 1
            except Exception as e:
                logger.error(f"Error processing MF row: {e}")
                continue
        
        logger.info(f"Successfully synced {count} Mutual Funds from Google Sheet.")
        return count
    except Exception as e:
        logger.error(f"Error syncing Mutual Funds: {e}")
        return 0

def sync_nps_from_sheet():
    """Sync NPS NAVs from Google Sheet (Tab: NPS)."""
    from core.models import NPSFund
    from decimal import Decimal
    
    # URL for the 'NPS' tab
    sheet_url = "https://docs.google.com/spreadsheets/d/12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4/gviz/tq?tqx=out:csv&sheet=NPS"
    
    try:
        response = requests.get(sheet_url, timeout=15)
        response.raise_for_status()
        
        # Column A: Scheme Name (iloc[0]), Column B: NAV Value (iloc[1])
        df = pd.read_csv(io.StringIO(response.text))
        
        count = 0
        for _, row in df.iterrows():
            try:
                name_val = row.iloc[0]
                if pd.isna(name_val): continue
                name = str(name_val).strip()
                if not name or name.lower() == 'nan': continue
                
                nav = clean_float(row.iloc[1], default=0.0) if len(row) > 1 else 0

                # Update or create NPSFund record
                fund, created = NPSFund.objects.get_or_create(name=name)
                
                # Store previous nav for day change calculation
                if not created:
                    fund.prev_nav = fund.nav
                
                fund.nav = Decimal(str(nav))
                fund.save()
                count += 1
            except Exception as e:
                logger.error(f"Error processing NPS row: {e}")
                continue
        
        logger.info(f"Successfully synced {count} NPS Funds from Google Sheet.")
        return count
    except Exception as e:
        logger.error(f"Error syncing NPS: {e}")
        return 0

def sync_coins_from_sheet():
    """Sync Cryptocurrency prices from Google Sheet (Tab: coin)."""
    from core.models import Coin
    from decimal import Decimal
    import math

    # URL for the 'coin' tab
    sheet_url = "https://docs.google.com/spreadsheets/d/12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4/gviz/tq?tqx=out:csv&sheet=coin"
    
    # Mapping for common coin names to symbols used in the DB
    NAME_TO_SYMBOL = {
        'Bitcoin': 'BTC-INR',
        'Bitcoin ': 'BTC-INR',
        'Ethereum': 'ETH-INR',
        'Ethereum ': 'ETH-INR',
        'Dogecoin': 'DOGE-INR',
        'Dogecoin ': 'DOGE-INR',
        'Solana': 'SOL-INR',
        'Solana ': 'SOL-INR',
        'Ripple': 'XRP-INR',
        'Ripple ': 'XRP-INR',
        'XRP': 'XRP-INR',
        'Cardano': 'ADA-INR',
        'Polygon': 'MATIC-INR',
        'Polkadot': 'DOT-INR',
        'Shiba Inu': 'SHIB-INR',
        'Litecoin': 'LTC-INR',
        'Tether': 'USDT-INR',
        'USDT': 'USDT-INR',
    }

    try:
        response = requests.get(sheet_url, timeout=15)
        response.raise_for_status()
        
        # Column A: Name (iloc[0]), Column B: Price (iloc[1])
        df = pd.read_csv(io.StringIO(response.text))
        
        count = 0
        for _, row in df.iterrows():
            try:
                name_val = row.iloc[0]
                if pd.isna(name_val): continue
                raw_name = str(name_val).strip()
                if not raw_name or raw_name.lower() == 'nan': continue
                
                # Determine Symbol: Check mapping, then if a Coin with this name exists, or use name itself
                symbol = NAME_TO_SYMBOL.get(raw_name) or NAME_TO_SYMBOL.get(raw_name.strip())
                if not symbol:
                    # Check if a coin already exists with this name as its symbol or name
                    existing = Coin.objects.filter(symbol__iexact=raw_name).first()
                    if not existing:
                        existing = Coin.objects.filter(name__iexact=raw_name).first()
                    
                    if existing:
                        symbol = existing.symbol
                    else:
                        symbol = raw_name.upper() # Fallback to upper case name
                        if '-' not in symbol:
                            symbol = f"{symbol}-INR"

                price = clean_float(row.iloc[1], default=0.0) if len(row) > 1 else 0
                if price <= 0: continue

                # Update or create Coin record
                coin = Coin.objects.filter(symbol=symbol).first()
                if coin:
                    coin.prev_price = coin.price
                    coin.price = Decimal(str(price))
                    coin.name = raw_name
                    coin.last_updated = timezone.now()
                    coin.save()
                else:
                    coin = Coin.objects.create(
                        symbol=symbol,
                        name=raw_name,
                        price=Decimal(str(price)),
                        prev_price=Decimal(str(price)),
                        last_updated=timezone.now()
                    )
                count += 1
            except Exception as e:
                logger.error(f"Error processing Coin row: {e}")
                continue
        
        logger.info(f"Successfully synced {count} Coins from Google Sheet.")
        return count
    except Exception as e:
        logger.error(f"Error syncing Coins: {e}")
        return 0

def fetch_live_ltp(force_fetch=False):
    """Fetch live LTP from Google Sheet CSV export with caching."""
    cache_key = 'live_ltp_data'
    data = cache.get(cache_key)
    
    if data is not None:
        return data

    if not force_fetch:
        # Prevent blocking synchronous HTTP requests during page load cycles.
        # Background scheduler / update_ltp command will run with force_fetch=True.
        logger.info("LTP cache miss in request thread; returning empty map to fallback on database prices.")
        return {}

    url = f"https://docs.google.com/spreadsheets/d/{settings.MASTER_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=n2g"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Read CSV, skipping first row as it might be header
        df = pd.read_csv(io.StringIO(response.text), skiprows=1)
        
        ltp_map = {}
        for _, row in df.iterrows():
            try:
                # Assuming Column 2 is Symbol and Column 4 is LTP based on other sync logic
                symbol = str(row.iloc[2]).strip().upper()
                ltp_val = row.iloc[4]
                
                if pd.notna(symbol) and pd.notna(ltp_val):
                    price = clean_float(ltp_val, default=0.0)
                    if price > 0:
                        ltp_map[symbol] = price
            except Exception:
                continue
                
        # Cache for 5 minutes
        cache.set(cache_key, ltp_map, 300)
        return ltp_map
        
    except Exception as e:
        logger.error(f"Error in fetch_live_ltp: {e}")
        return {}

def fetch_strategy_stocks():
    """Fetch recommended stocks for each strategy from the database (synced from Google Sheets)."""
    from core.models import Strategy
    
    # Use cache to avoid frequent DB hits if preferred, though DB is already fast
    cache_key = 'strategy_stocks_db_v1'
    cached = cache.get(cache_key)
    if cached:
        return cached

    result = {}
    strategies = Strategy.objects.all().prefetch_related('stocks')
    for strategy in strategies:
        result[strategy.name] = list(strategy.stocks.values_list('symbol', flat=True))
    
    if result:
        cache.set(cache_key, result, 300) # cache for 5 minutes
    return result

def record_portfolio_value_history(user):
    """
    Calculate and record the current total portfolio value for the history tracking.
    This should be called periodically or when user visits significant pages.
    """
    from core.models import (
        Portfolio, MFPortfolio, CoinPortfolio, NPSPortfolio, 
        FixedAsset, OtherAsset, PortfolioValueHistory,
        PnLStatement, Loan, Transaction
    )
    from django.utils import timezone
    from decimal import Decimal
    from django.db.models import Sum, F
    
    # --- Self-Healing Sync: Ensure Portfolio matches Transaction lots ---
    active_lots = Transaction.objects.filter(user=user, transaction_type='BUY', remaining_quantity__gt=0).values('instrument').annotate(
        total_qty=Sum('remaining_quantity'),
        total_cost=Sum(F('remaining_quantity') * F('price'))
    )
    active_ids = set()
    for lot in active_lots:
        iid = lot['instrument']
        t_qty = lot['total_qty']
        a_cost = lot['total_cost'] / t_qty if t_qty > 0 else 0
        active_ids.add(iid)
        p_item, created = Portfolio.objects.get_or_create(user=user, instrument_id=iid, defaults={'quantity': t_qty, 'avg_cost': a_cost})
        if not created and (p_item.quantity != t_qty or abs(p_item.avg_cost - a_cost) > 0.01):
            p_item.quantity = t_qty
            p_item.avg_cost = a_cost
            p_item.save(update_fields=['quantity', 'avg_cost'])
    Portfolio.objects.filter(user=user).exclude(instrument_id__in=active_ids).delete()
    # --------------------------------------------------------------------

    today = timezone.localdate()
    
    # 1. Stocks/ETFs
    stocks = Portfolio.objects.filter(user=user)
    stock_invested = sum(p.invested_amount for p in stocks)
    stock_current = sum(p.current_value for p in stocks)
    
    # 2. Mutual Funds
    mfs = MFPortfolio.objects.filter(user=user)
    mf_invested = sum(p.invested_amount for p in mfs)
    mf_current = sum(p.current_value for p in mfs)
    
    # 3. Coins (Crypto)
    coins = CoinPortfolio.objects.filter(user=user)
    coin_invested = sum(p.invested_amount for p in coins)
    coin_current = sum(p.current_value for p in coins)
    
    # 4. NPS
    nps = NPSPortfolio.objects.filter(user=user)
    nps_invested = sum(p.invested_amount for p in nps)
    nps_current = sum(p.current_value for p in nps)
    
    # 5. Fixed Assets (FD, PPF, etc.)
    fds = FixedAsset.objects.filter(user=user)
    fd_invested = sum(p.invested_amount_decimal for p in fds)
    fd_current = sum(Decimal(str(p.current_value)) for p in fds)
    
    # 6. Other Assets (Real Estate, Gold, etc.)
    others = OtherAsset.objects.filter(user=user)
    other_invested = sum(p.purchase_price for p in others)
    other_current = sum(p.current_value for p in others)
    
    # 7. Liabilities (Deduct from Net Worth)
    loans = Loan.objects.filter(user=user, is_active=True)
    loan_outstanding = sum(l.current_outstanding for l in loans)
    
    total_invested = Decimal(stock_invested) + Decimal(mf_invested) + Decimal(coin_invested) + Decimal(nps_invested) + Decimal(fd_invested) + Decimal(other_invested)
    total_current = Decimal(stock_current) + Decimal(mf_current) + Decimal(coin_current) + Decimal(nps_current) + Decimal(fd_current) + Decimal(other_current)
    net_worth = total_current - Decimal(str(loan_outstanding))
    
    # 8. Benchmark (NIFTY 50)
    from core.models import MarketTicker
    nifty = MarketTicker.objects.filter(name='NIFTY 50').first()
    n_p = Decimal(str(nifty.price)) if nifty else None
    
    if total_invested > 0 or total_current > 0:
        PortfolioValueHistory.objects.update_or_create(
            user=user,
            date=today,
            defaults={
                'invested_value': total_invested,
                'current_value': total_current,
                'net_worth': net_worth,
                'stock_invested': Decimal(stock_invested),
                'stock_current': Decimal(stock_current),
                'mf_invested': Decimal(mf_invested),
                'mf_current': Decimal(mf_current),
                'coin_invested': Decimal(coin_invested),
                'coin_current': Decimal(coin_current),
                'nps_invested': Decimal(nps_invested),
                'nps_current': Decimal(nps_current),
                'nifty_price': n_p
            }
        )

def record_all_portfolio_history():
    """Run history recording for all users in the system."""
    from django.contrib.auth.models import User
    users = User.objects.all()
    count = 0
    for user in users:
        record_portfolio_value_history(user)
        count += 1
    return count

def get_recommendations(user, is_consolidated=False):
    """
    Calculate buy/sell recommendations for a given user or consolidated family portfolio.
    """
    from core.models import Portfolio, PnLStatement, Instrument, Profile, FamilyLink, Transaction
    from django.db.models.functions import Upper
    from django.db.models import Sum, Count
    from django.db import models
    from django.contrib.auth.models import User
    
    if is_consolidated:
        linked_users = FamilyLink.objects.filter(user=user, is_verified=True).values_list('family_user', flat=True)
        user_list = [user.id] + list(linked_users)
        portfolio_items_query = Portfolio.objects.filter(user_id__in=user_list).select_related('instrument')
        pnl_items_query = PnLStatement.objects.filter(user_id__in=user_list).select_related('instrument')
    else:
        portfolio_items_query = Portfolio.objects.filter(user=user).select_related('instrument')
        pnl_items_query = PnLStatement.objects.filter(user=user).select_related('instrument')
    
    live_ltps = fetch_live_ltp() or {}
    
    # Aggregate Realized Profit per Instrument across all target users
    realized_profits_qs = pnl_items_query.annotate(
        symbol_upper=Upper('instrument__symbol')
    ).values('symbol_upper').annotate(
        total_profit=Sum('realized_profit')
    )
    realized_profits = {item['symbol_upper'].upper(): float(item['total_profit']) for item in realized_profits_qs}

    # Count lots per instrument
    lot_counts_qs = Transaction.objects.filter(
        user_id__in=user_list if is_consolidated else [user.id],
        transaction_type='BUY',
        remaining_quantity__gt=0
    ).annotate(
        symbol_upper=Upper('instrument__symbol')
    ).values('symbol_upper').annotate(
        count=Count('id')
    )
    lot_counts = {item['symbol_upper'].upper(): item['count'] for item in lot_counts_qs}

    # Aggregate Portfolio items across all target users
    # We group by instrument symbol
    agg_portfolio = {}
    for item in portfolio_items_query:
        sym = item.instrument.symbol.upper()
        if sym not in agg_portfolio:
            agg_portfolio[sym] = {
                'instrument': item.instrument,
                'quantity': 0,
                'invested_amount': 0,
                'ltp': item.ltp, # base ltp
                'notes': item.notes,
            }
        agg_portfolio[sym]['quantity'] += item.quantity
        agg_portfolio[sym]['invested_amount'] += float(item.quantity) * float(item.avg_cost)
        if not agg_portfolio[sym]['notes'] and item.notes:
            agg_portfolio[sym]['notes'] = item.notes

    # Map symbols to strategies
    strategy_stocks = fetch_strategy_stocks()
    symbol_to_strategy = {}
    for s_key, s_list in strategy_stocks.items():
        for s in s_list:
            symbol_to_strategy[s.upper()] = s_key

    def get_factor_j(lh_diff):
        if lh_diff is None: return 1.0
        lh_diff = float(lh_diff)
        if lh_diff <= 2: return 0.5
        if lh_diff <= 5: return 0.55
        if lh_diff <= 8: return 0.6
        if lh_diff <= 12: return 0.68
        if lh_diff <= 18: return 0.75
        if lh_diff <= 25: return 0.85
        if lh_diff <= 35: return 0.92
        return 0.97

    def get_factor_i(pe):
        if pe is None or pe == 0: return 0.3
        pe = float(pe)
        if pe < 0: return 0.3333333333
        if pe == 50: return 1.0
        if pe > 50: return 50.0 / pe
        return 1.0

    # Profile for recommendation logic uses the PRIMARY user's settings even in consolidated
    profile, _ = Profile.objects.get_or_create(user=user)
    recommendations = []

    for symbol, data in agg_portfolio.items():
        inst = data['instrument']
        quantity = data['quantity']
        invested = data['invested_amount']
        avg_cost = invested / quantity if quantity > 0 else 0
        
        ltp = float(live_ltps.get(symbol, 0))
        if ltp <= 0:
            try:
                ltp = float(inst.last_price)
            except (AttributeError, ValueError, TypeError):
                ltp = 0
        if ltp <= 0:
            ltp = float(data['ltp'])
        
        current = quantity * ltp
        unrealized = current - invested
        unrealized_pct = (unrealized / invested * 100) if invested else 0
        
        realized_profit = realized_profits.get(symbol, 0)
        strat_key = symbol_to_strategy.get(symbol, 'moderate')
        initial_inv = float(profile.get_max_investment(strat_key))
        
        factor_j = get_factor_j(inst.diff_from_lh_pct)
        factor_i = get_factor_i(inst.pe_ratio)
        
        buy_gap_formula = (realized_profit * 0.93 - invested) + (initial_inv * factor_j * factor_i)
        
        profit_target = float(profile.equity_profit_expectation)
        # Suppress SELL if Realized Profit > Current Investment (keep averaging instead)
        can_sell = realized_profit <= invested
        if unrealized_pct >= profit_target and can_sell:
            action = "SELL"
            reason = f"Pft > {profit_target}%"
        elif -3000 <= buy_gap_formula <= 3000:
            action = "HOLD"
            reason = f"TgtCap: {buy_gap_formula:.0f}"
        elif buy_gap_formula > 3000:
            action = "BUY"
            reason = f"TgtCap: {buy_gap_formula:.0f}"
        elif buy_gap_formula < -3000:
            action = "REDUCE"
            reason = f"TgtCap: {buy_gap_formula:.0f}"
        else:
            action = "HOLD"
            reason = "Stable"

        buy_gap = buy_gap_formula if action == 'BUY' else 0
        reduce_gap = abs(buy_gap_formula) if action == 'REDUCE' else 0

        # Day Change Calculations
        absolute_change = float(inst.price_change or 0)
        previous_close = float(inst.previous_close or 0)
        
        if previous_close <= 0:
            previous_close = ltp - absolute_change
            
        day_change = absolute_change
        total_day_change_item = absolute_change * quantity
        day_change_pct = (absolute_change / previous_close * 100) if previous_close > 0 else 0

        qty_can_sell = 0
        if ltp > 0:
            qty_can_sell = int(abs(quantity - ((realized_profit + unrealized) / ltp)))

        recommendations.append({
            'symbol': symbol,
            'name': inst.name,
            'quantity': quantity,
            'avg_cost': avg_cost,
            'ltp': ltp,
            'invested_amount': round(invested, 2),
            'current_value': round(current, 2),
            'unrealized_pnl': round(unrealized, 2),
            'pnl_percent': round(unrealized_pct, 2),
            'day_change': round(day_change, 2),
            'total_day_change': round(total_day_change_item, 2),
            'day_change_pct': round(day_change_pct, 2),
            'previous_close': round(previous_close, 2),
            'action': action,
            'reason': reason,
            'instrument_id': inst.id,
            'buy_gap': round(buy_gap, 2),
            'reduce_gap': round(reduce_gap, 2),
            'target_capital': buy_gap_formula,
            'target_qty': round(buy_gap_formula / ltp) if ltp > 0 else 0,
            'target_qty_abs': abs(round(buy_gap_formula / ltp)) if ltp > 0 else 0,
            'realized_profit': realized_profit,
            'qty_can_sell': qty_can_sell,
            'in_portfolio': True if quantity > 0 else False,
            'lot_count': lot_counts.get(symbol, 0),
            'notes': data.get('notes', ''),
        })
    
    # Add P&L-only stocks
    portfolio_symbols = set(agg_portfolio.keys())
    for symbol, realized_profit in realized_profits.items():
        if symbol not in portfolio_symbols:
            inst = Instrument.objects.filter(symbol__iexact=symbol).first()
            if not inst: continue
            
            ltp = float(live_ltps.get(symbol, 0))
            if ltp <= 0: ltp = float(inst.last_price or 0)

            strat_key = symbol_to_strategy.get(symbol, 'moderate')
            initial_inv = float(profile.get_max_investment(strat_key))
            factor_j = get_factor_j(inst.diff_from_lh_pct)
            factor_i = get_factor_i(inst.pe_ratio)
            
            buy_gap_formula = (realized_profit * 0.93) + (initial_inv * factor_j * factor_i)
            
            if -3000 <= buy_gap_formula <= 3000:
                action = "HOLD"
                reason = f"TgtCap: {buy_gap_formula:.0f}"
            elif buy_gap_formula > 3000:
                action = "BUY"
                reason = f"TgtCap: {buy_gap_formula:.0f}"
            elif buy_gap_formula < -3000:
                action = "REDUCE"
                reason = f"TgtCap: {buy_gap_formula:.0f}"
            else:
                action = "HOLD"
                reason = "Stable"


            buy_gap = buy_gap_formula if action == 'BUY' else 0
            reduce_gap = abs(buy_gap_formula) if action == 'REDUCE' else 0

            absolute_change = float(inst.price_change or 0)
            previous_close = float(inst.previous_close or 0)
            if previous_close <= 0:
                previous_close = ltp - absolute_change
            day_change_pct = (absolute_change / previous_close * 100) if previous_close > 0 else 0

            recommendations.append({
                'symbol': symbol,
                'name': inst.name,
                'quantity': 0,
                'avg_cost': 0,
                'ltp': ltp,
                'invested_amount': 0,
                'current_value': 0,
                'unrealized_pnl': 0,
                'pnl_percent': 0,
                'day_change': round(absolute_change, 2),
                'day_change_pct': round(day_change_pct, 2),
                'action': action,
                'reason': reason,
                'buy_gap': round(buy_gap, 2),
                'reduce_gap': round(reduce_gap, 2),
                'target_capital': buy_gap_formula,
                'target_qty': round(buy_gap_formula / ltp) if ltp > 0 else 0,
                'target_qty_abs': abs(round(buy_gap_formula / ltp)) if ltp > 0 else 0,
                'realized_profit': realized_profit,
                'in_portfolio': False,
                'instrument_id': inst.id,
            })
        
    # Add Strategy symbols not in portfolio or P&L
    all_strategy_symbols = set()
    for s_list in strategy_stocks.values():
        all_strategy_symbols.update(s_list)
    
    processed_symbols = portfolio_symbols.union(set(realized_profits.keys()))
    
    for symbol in all_strategy_symbols:
        symbol = symbol.upper()
        if symbol not in processed_symbols:
            inst = Instrument.objects.filter(symbol__iexact=symbol).first()
            ltp = float(live_ltps.get(symbol, 0))
            if inst and ltp <= 0: ltp = float(inst.last_price or 0)
            
            strat_key = symbol_to_strategy.get(symbol, 'moderate')
            initial_inv = float(profile.get_max_investment(strat_key))
            
            factor_j = 1.0; factor_i = 1.0
            if inst:
                factor_j = get_factor_j(inst.diff_from_lh_pct)
                factor_i = get_factor_i(inst.pe_ratio)
            
            buy_gap_formula = initial_inv * factor_j * factor_i
            
            if -3000 <= buy_gap_formula <= 3000:
                action = "HOLD"
                reason = f"TgtCap: {buy_gap_formula:.0f}"
            elif buy_gap_formula > 3000:
                action = "BUY"
                reason = f"TgtCap: {buy_gap_formula:.0f}"
            elif buy_gap_formula < -3000:
                action = "REDUCE"
                reason = f"TgtCap: {buy_gap_formula:.0f}"
            else:
                action = "HOLD"
                reason = "Stable"


            buy_gap = buy_gap_formula if action == 'BUY' else 0
            reduce_gap = abs(buy_gap_formula) if action == 'REDUCE' else 0

            # Day Change Calculations
            absolute_change = float(inst.price_change or 0) if inst else 0
            previous_close = float(inst.previous_close or 0) if inst else 0
            if inst and previous_close <= 0:
                previous_close = ltp - absolute_change
            day_change_pct = (absolute_change / previous_close * 100) if previous_close > 0 else 0

            recommendations.append({
                'symbol': symbol,
                'name': inst.name if inst else symbol,
                'quantity': 0,
                'avg_cost': 0,
                'ltp': ltp,
                'invested_amount': 0,
                'current_value': 0,
                'unrealized_pnl': 0,
                'pnl_percent': 0,
                'day_change': round(absolute_change, 2),
                'day_change_pct': round(day_change_pct, 2),
                'action': action,
                'reason': reason,
                'buy_gap': round(buy_gap, 2),
                'reduce_gap': round(reduce_gap, 2),
                'target_capital': buy_gap_formula,
                'target_qty': round(buy_gap_formula / ltp) if ltp > 0 else 0,
                'target_qty_abs': abs(round(buy_gap_formula / ltp)) if ltp > 0 else 0,
                'realized_profit': 0,
                'in_portfolio': False,
                'instrument_id': inst.id if inst else None,
            })
            
    # Filter out Hidden Signals (only for BUY signals where quantity is 0)
    from core.models import HiddenSignal
    hidden_ids = set(HiddenSignal.objects.filter(user=user).values_list('instrument_id', flat=True))
    
    if hidden_ids:
        recommendations = [
            r for r in recommendations
            if not (r.get('instrument_id') in hidden_ids and r.get('quantity', 0) == 0 and r.get('action') == 'BUY')
        ]
            
    return recommendations, realized_profits, strategy_stocks
def get_target_user(request):
    """
    Identifies the target user for portfolio views and actions.
    Handles family link verification for user_id in GET or POST parameters.
    Returns (target_user, is_family_view, is_consolidated)
    """
    from django.contrib.auth.models import User
    from .models import FamilyLink
    
    target_user = request.user
    is_family_view = False
    is_consolidated = False
    
    if not request.user.is_authenticated:
        return target_user, is_family_view, is_consolidated

    # Support both GET (views) and POST (actions like buy/sell)
    user_id = request.POST.get('user_id') or request.GET.get('user_id')
    
    if user_id == 'consolidated':
        is_consolidated = True
    elif user_id:
        try:
            # Verify the link exists and is verified
            link = FamilyLink.objects.filter(user=request.user, family_user_id=user_id, is_verified=True).first()
            if link:
                target_user = link.family_user
                is_family_view = True
            elif str(user_id) == str(request.user.id):
                # Requesting self
                pass
            else:
                # Permission denied or link not found/unverified
                pass
        except (ValueError, TypeError):
            pass
            
    return target_user, is_family_view, is_consolidated

def get_consolidated_users(user):
    """Returns a list of User IDs for the user and all verified family members."""
    from .models import FamilyLink
    linked_users = FamilyLink.objects.filter(user=user, is_verified=True).values_list('family_user_id', flat=True)
    return [user.id] + list(linked_users)

def get_portfolio_summary_metrics(user):
    """
    Calculates comprehensive portfolio metrics for a user.
    Returns a dictionary suitable for template context.
    """
    from core.models import Portfolio, MFPortfolio, CoinPortfolio, NPSPortfolio, Loan, FixedAsset, OtherAsset
    
    # 1. Get Recommendations (Signals)
    recommendations, realized_profits, _ = get_recommendations(user)
    
    # Filter signals (matching dashboard logic)
    user_signals = [
        r for r in recommendations 
        if r.get('in_portfolio', False) or (r.get('action') == 'BUY' and r.get('realized_profit', 0) > 0)
    ]
    
    buy_count = sum(1 for r in user_signals if r.get('action') == 'BUY')
    reduce_count = sum(1 for r in user_signals if r.get('action') == 'REDUCE')
    sell_count = sum(1 for r in user_signals if r.get('action') == 'SELL')
    total_signals = buy_count + reduce_count + sell_count

    # 2. Calculate Portfolio Metrics
    # Stocks
    stocks = Portfolio.objects.filter(user=user)
    stocks_invested = sum(p.invested_amount for p in stocks)
    stocks_current = sum(p.current_value for p in stocks)
    stocks_realized = float(sum(realized_profits.values()) if isinstance(realized_profits, dict) else 0)

    # Mutual Funds
    mf_holdings = MFPortfolio.objects.filter(user=user)
    mf_invested = float(sum(h.invested_amount for h in mf_holdings))
    mf_current = float(sum(h.current_value for h in mf_holdings))
    mf_realized = float(sum(h.realized_profit for h in mf_holdings))

    # Coins
    coin_holdings = CoinPortfolio.objects.filter(user=user)
    coin_invested = float(sum(h.invested_amount for h in coin_holdings))
    coin_current = float(sum(h.current_value for h in coin_holdings))
    coin_realized = float(sum(h.realized_profit for h in coin_holdings))

    # NPS
    nps_holdings = NPSPortfolio.objects.filter(user=user)
    nps_invested = float(sum(h.invested_amount for h in nps_holdings))
    nps_current = float(sum(h.current_value for h in nps_holdings))
    nps_realized = float(sum(h.realized_profit for h in nps_holdings))

    # Fixed Assets
    fd_holdings = FixedAsset.objects.filter(user=user)
    fd_invested = float(sum(h.invested_amount_decimal for h in fd_holdings))
    fd_current = float(sum(h.current_value for h in fd_holdings))

    # Other Assets
    other_holdings = OtherAsset.objects.filter(user=user)
    other_invested = float(sum(h.purchase_price for h in other_holdings))
    other_current = float(sum(h.current_value for h in other_holdings))

    # Loans
    loans = Loan.objects.filter(user=user, is_active=True)
    loan_outstanding = float(sum(l.current_outstanding for l in loans))

    # Aggregates
    total_invested = float(stocks_invested) + mf_invested + coin_invested + nps_invested + fd_invested + other_invested
    total_current_assets = float(stocks_current) + mf_current + coin_current + nps_current + fd_current + other_current
    
    # Portfolio Value (Equity/Assets)
    portfolio_value = total_current_assets
    # Liabilities
    liabilities = loan_outstanding
    # Realized
    total_realized_profit = stocks_realized + mf_realized + coin_realized + nps_realized
    # Unrealized (Asset Current - Asset Invested)
    total_unrealized_pnl = total_current_assets - total_invested

    return {
        'portfolio_value': portfolio_value,
        'initial_capital': total_invested,
        'unrealized_pnl': total_unrealized_pnl,
        'total_realized': total_realized_profit,
        'liabilities': liabilities,
        'buy_count': buy_count,
        'reduce_count': reduce_count,
        'sell_count': sell_count,
        'total_count': total_signals
    }


def recalculate_instrument_lots(user, instrument):
    """
    Re-processes all BUY/SELL transactions for an instrument to ensure correct FIFO/Intraday matching.
    Crucially, it processes BUYs before SELLs on the same day to handle 'Sell then Buy' intraday scenarios.
    """
    from core.models import Transaction, PnLStatement, Portfolio, Profile
    from decimal import Decimal
    from django.db.models import F
    from django.db import transaction as db_transaction

    with db_transaction.atomic():
        # 1. Reset all BUY lots for this user/instrument
        Transaction.objects.filter(user=user, instrument=instrument, transaction_type='BUY').update(remaining_quantity=F('quantity'))
        # 2. Delete all existing PnL for this user/instrument
        PnLStatement.objects.filter(user=user, instrument=instrument).delete()
        
        # 3. Get all transactions, ordered to prioritize BUYs on the same day
        # 'BUY' < 'SELL' alphabetically, so they come first with ascending order
        all_txs = Transaction.objects.filter(user=user, instrument=instrument).order_by('date', 'transaction_type', 'created_at')
        
        buy_lots = []
        for tx in all_txs:
            if tx.transaction_type == 'BUY':
                buy_lots.append(tx)
                continue
            
            # Process SELL
            remaining_to_deduct = tx.quantity
            total_buy_value = Decimal('0')
            first_entry_date = None
            is_intraday = False
            
            # Priority 0: Manual Match (Specific Lot)
            if tx.matched_buy_id:
                lot = next((l for l in buy_lots if l.id == tx.matched_buy_id), None)
                if lot and lot.remaining_quantity > 0:
                    deduct = min(lot.remaining_quantity, remaining_to_deduct)
                    total_buy_value += Decimal(str(deduct)) * lot.price
                    lot.remaining_quantity -= deduct
                    remaining_to_deduct -= deduct
                    if first_entry_date is None: first_entry_date = lot.date
                    if lot.date == tx.date: is_intraday = True

            # Priority 1: Intraday (Same Day)
            if remaining_to_deduct > 0:
                # Find buys on the same day
                intraday_lots = [l for l in buy_lots if l.date == tx.date and l.remaining_quantity > 0]
                
                # Prioritize matching same trade_type (e.g., INTRADAY sell with INTRADAY buy)
                intraday_lots.sort(key=lambda l: l.trade_type != tx.trade_type)
                
                for lot in intraday_lots:
                    if remaining_to_deduct <= 0: break
                    deduct = min(lot.remaining_quantity, remaining_to_deduct)
                    total_buy_value += Decimal(str(deduct)) * lot.price
                    lot.remaining_quantity -= deduct
                    remaining_to_deduct -= deduct
                    if first_entry_date is None: first_entry_date = lot.date
                    is_intraday = True

            # Priority 2: FIFO (Oldest)
            # Standard FIFO only applies if it's NOT an Intraday Sell, 
            # or if it's an Intraday Sell but we allow overflow (usually we don't for tax reasons)
            if remaining_to_deduct > 0 and tx.trade_type != 'INTRADAY':
                # buy_lots is already sorted by date
                for lot in buy_lots:
                    if lot.remaining_quantity <= 0: continue
                    if remaining_to_deduct <= 0: break
                    deduct = min(lot.remaining_quantity, remaining_to_deduct)
                    total_buy_value += Decimal(str(deduct)) * lot.price
                    lot.remaining_quantity -= deduct
                    remaining_to_deduct -= deduct
                    if first_entry_date is None: first_entry_date = lot.date

            # Calculate Profit and Record PnL
            profile, _ = Profile.objects.get_or_create(user=user)
            if is_intraday:
                fixed_charge = profile.intraday_fixed_charge or Decimal('0')
                pct_charge = profile.intraday_brokerage_pct if profile.intraday_brokerage_pct is not None else Decimal('0')
            else:
                fixed_charge = profile.equity_fixed_charge or Decimal('0')
                pct_charge = profile.equity_brokerage_pct if profile.equity_brokerage_pct is not None else Decimal('0')
            
            # USER REQUEST: Do not deduct brokerage from sell value during recalculation 
            # to avoid double-deducting from historically synced 'Net' prices.
            sell_brokerage = Decimal('0')
            sell_value_net = (tx.price * Decimal(str(tx.quantity)))
            profit = sell_value_net - total_buy_value
            
            PnLStatement.objects.create(
                user=user, instrument=instrument,
                entry_date=first_entry_date,
                quantity=tx.quantity,
                buy_value=total_buy_value,
                sell_value=sell_value_net,
                realized_profit=profit,
                exit_date=tx.date,
                trade_type=tx.trade_type
            )
            
        # 4. Finalize - save lot quantities
        for lot in buy_lots:
            lot.save(update_fields=['remaining_quantity'])
            
        # 5. Update Portfolio
        total_remaining = sum(l.remaining_quantity for l in buy_lots)
        total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in buy_lots)
        
        portfolio = Portfolio.objects.filter(user=user, instrument=instrument).first()
        if total_remaining <= 0:
            if portfolio: portfolio.delete()
        else:
            if not portfolio:
                portfolio = Portfolio(user=user, instrument=instrument)
            portfolio.quantity = total_remaining
            portfolio.avg_cost = total_cost / Decimal(str(total_remaining)) if total_remaining > 0 else 0
            # Ensure LTP is set to prevent IntegrityError in MySQL
            portfolio.ltp = instrument.last_price or Decimal('0')
            portfolio.save()


def execute_stock_sell(user, instrument, quantity_to_sell, price, exit_date=None, target_lot_id=None, trade_type='NORMAL'):
    """
    Simplified sell logic: records the transaction and triggers a full lot recalculation.
    Supports Intraday validation.
    """
    from core.models import Transaction, Portfolio, PnLStatement
    from django.core.exceptions import ValidationError
    import pandas as pd
    from django.db.models import Sum

    if not exit_date:
        exit_date = timezone.localdate()
    elif isinstance(exit_date, str):
        exit_date = pd.to_datetime(exit_date).date()
        
    if exit_date > timezone.localdate():
        raise ValidationError("Exit date cannot be in the future.")
        
    # Intraday Validation
    if trade_type == 'INTRADAY':
        buy_qty = Transaction.objects.filter(
            user=user, 
            instrument=instrument, 
            date=exit_date, 
            transaction_type='BUY', 
            trade_type='INTRADAY'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        sell_qty = Transaction.objects.filter(
            user=user, 
            instrument=instrument, 
            date=exit_date, 
            transaction_type='SELL', 
            trade_type='INTRADAY'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        available_intraday = buy_qty - sell_qty
        
        if buy_qty == 0:
            raise ValidationError("Same day Intraday Buy entry not found. Please first add Intraday Buy entry and then do Intraday Sell.")
        
        if quantity_to_sell > available_intraday:
            raise ValidationError(f"Quantity exceeds same day bought quantity. Available to sell intraday: {available_intraday}")
    else:
        # Normal Sell Validation
        portfolio = Portfolio.objects.filter(user=user, instrument_id=instrument.id).first()
        if not portfolio or quantity_to_sell > portfolio.quantity:
            available = portfolio.quantity if portfolio else 0
            raise ValidationError(f"Insufficient quantity. You have {available} units of {instrument.symbol}.")

    # Record Sell Transaction
    Transaction.objects.create(
        user=user,
        instrument=instrument,
        transaction_type='SELL',
        trade_type=trade_type,
        quantity=quantity_to_sell,
        price=price,
        date=exit_date,
        matched_buy_id=target_lot_id
    )
    
    # Trigger Recalculation
    recalculate_instrument_lots(user, instrument)
    
    # Get profit from the last PnLStatement for this sell
    pnl = PnLStatement.objects.filter(user=user, instrument=instrument, exit_date=exit_date).order_by('-id').first()
    profit = pnl.realized_profit if pnl else 0
    is_intraday_pnl = (pnl.entry_date == pnl.exit_date) if pnl else False
    
    return profit, is_intraday_pnl

def execute_stock_buy(user, instrument, quantity, avg_cost, transaction_date=None, notes=None, trade_type='NORMAL'):
    """
    Simplified buy logic: records the transaction (with brokerage) and triggers a lot recalculation.
    """
    from core.models import Transaction, Portfolio, Profile
    from decimal import Decimal
    
    if not transaction_date:
        transaction_date = timezone.localdate()
    elif isinstance(transaction_date, str):
        import pandas as pd
        transaction_date = pd.to_datetime(transaction_date).date()

    # Calculate Brokerage for BUY
    profile, _ = Profile.objects.get_or_create(user=user)
    
    if trade_type == 'INTRADAY':
        fixed_charge = profile.intraday_fixed_charge or Decimal('0')
        pct_charge = profile.intraday_brokerage_pct if profile.intraday_brokerage_pct is not None else Decimal('0')
    else:
        fixed_charge = profile.equity_fixed_charge or Decimal('0')
        pct_charge = profile.equity_brokerage_pct if profile.equity_brokerage_pct is not None else Decimal('0')
        
    total_brokerage = Decimal(str(fixed_charge)) + (Decimal(str(avg_cost)) * Decimal(str(quantity)) * Decimal(str(pct_charge)) / 100)
    price_with_brokerage = ((Decimal(str(avg_cost)) * Decimal(str(quantity))) + total_brokerage) / Decimal(str(quantity))

    # Create Transaction record
    Transaction.objects.create(
        user=user,
        instrument=instrument,
        transaction_type='BUY',
        trade_type=trade_type,
        quantity=quantity,
        remaining_quantity=quantity,
        price=price_with_brokerage,
        date=transaction_date
    )

    # Trigger Recalculation
    recalculate_instrument_lots(user, instrument)
    
    # Update notes if provided
    if notes:
        portfolio = Portfolio.objects.filter(user=user, instrument=instrument).first()
        if portfolio:
            portfolio.notes = notes
            portfolio.save(update_fields=['notes'])
            
    return Portfolio.objects.filter(user=user, instrument=instrument).first()


def send_blog_notification(post):
    """
    Sends an email notification to all active registered users when a new blog post is published.
    This runs asynchronously in a background thread to prevent blocking request execution.
    """
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.conf import settings
    import threading
    import logging

    logger = logging.getLogger(__name__)
    User = get_user_model()

    # Query active users and their names on the main thread to avoid DB locking in threads
    users_data = []
    for user in User.objects.filter(is_active=True):
        if user.email:
            profile = getattr(user, 'profile', None)
            user_name = profile.full_name if profile and profile.full_name else user.username
            users_data.append({
                'email': user.email,
                'name': user_name
            })

    subject = f"New Blog Post: {post.title} - FOLIUX"
    site_url = getattr(settings, 'SITE_URL', 'https://foliux.com')

    # Serialize post data to dictionary to avoid DB calls (e.g. lazy field loading) inside the thread
    post_data = {
        'title': post.title,
        'excerpt': post.excerpt,
        'get_absolute_url': post.get_absolute_url()
    }

    def _send():
        for user_info in users_data:
            try:
                context = {
                    'user_name': user_info['name'],
                    'post': post_data,
                    'site_url': site_url,
                }
                html_message = render_to_string('emails/new_blog_post.html', context)
                plain_message = strip_tags(html_message)

                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user_info['email']],
                    html_message=html_message,
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"Failed to send blog email to {user_info['email']}: {e}")

    threading.Thread(target=_send).start()

