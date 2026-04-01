from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
try:
    from allauth.account.forms import SetPasswordForm as AllauthSetPasswordForm
except ImportError:
    AllauthSetPasswordForm = DjangoSetPasswordForm

from .models import (
    Portfolio, PnLStatement, Instrument, Profile, OTP, Transaction, 
    SignupOTP, MarketTicker, Strategy, MutualFund, MFPortfolio, MFTransaction,
    Coin, CoinPortfolio, CoinTransaction,
    NPSFund, NPSPortfolio, NPSTransaction, FixedAsset, OtherAsset,
    Loan, LoanPayment
)
from .forms import (
    UploadFileForm, PortfolioForm, ManualPortfolioForm, 
    CustomUserCreationForm, ProfileForm, ForgotPasswordForm, 
    VerifyOTPForm, SetPasswordForm, EditLotForm,
    LoanForm, LoanPaymentForm
)
from .utils import fetch_live_ltp, perform_sync, get_recommendations, fetch_strategy_stocks
import random
import json
import yfinance as yf
import pandas as pd
import math
from decimal import Decimal, InvalidOperation

import logging
import logging
logger = logging.getLogger(__name__)

def _auto_update_mf():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import MutualFund
        from decimal import Decimal
        import yfinance as yf
        import pandas as pd
        
        ten_mins_ago = timezone.now() - timedelta(minutes=10)
        stale_funds = MutualFund.objects.filter(last_updated__lt=ten_mins_ago)
        if not stale_funds.exists(): return
        
        symbols = list(set([f.symbol for f in stale_funds if f.symbol]))
        if not symbols: return
        
        if len(symbols) == 1:
            ticker = yf.Ticker(symbols[0])
            hist = ticker.history(period="1d")
            if not hist.empty:
                val = hist['Close'].iloc[-1]
                for f in stale_funds:
                    if f.symbol == symbols[0]:
                        f.prev_nav = f.nav
                        f.nav = Decimal(str(val))
                        f.save()
        else:
            data = yf.download(symbols, period="1d", progress=False)
            close_data = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data[['Close']]
            for f in stale_funds:
                if f.symbol in close_data.columns:
                    val = close_data[f.symbol].iloc[-1]
                    if not pd.isna(val):
                        f.prev_nav = f.nav
                        f.nav = Decimal(str(val))
                        f.save()
    except Exception as e:
        logger.error(f"Auto update MF failed: {e}")

def _auto_update_coin():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import Coin
        from decimal import Decimal
        import requests
        
        ten_mins_ago = timezone.now() - timedelta(minutes=10)
        stale_coins = Coin.objects.filter(last_updated__lt=ten_mins_ago)
        if not stale_coins.exists(): return
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        for symbol in set([c.symbol for c in stale_coins if c.symbol]):
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                response = requests.get(url, headers=headers, timeout=5)
                price_val = response.json()['chart']['result'][0]['meta']['regularMarketPrice']
                for c in stale_coins:
                    if c.symbol == symbol and price_val:
                        c.prev_price = c.price
                        c.price = Decimal(str(price_val))
                        c.save()
            except Exception: pass
    except Exception as e:
        logger.error(f"Auto update Coin failed: {e}")

def _auto_update_nps():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import NPSFund
        from .utils import sync_nps_from_sheet
        
        ten_mins_ago = timezone.now() - timedelta(minutes=10)
        stale_funds = NPSFund.objects.filter(last_updated__lt=ten_mins_ago)
        if stale_funds.exists():
            sync_nps_from_sheet()
    except Exception as e:
        logger.error(f"Auto update NPS failed: {e}")
@login_required
def forgot_password_session(request):
    user = request.user
    if not user.email:
        messages.error(request, "No email address found for your account. Please update your profile.")
        return redirect('edit_profile')
    
    # Generate 6-digit OTP
    code = str(random.randint(100000, 999999))
    
    # Save OTP
    OTP.objects.filter(user=user).delete()
    OTP.objects.create(user=user, code=code)
    
    # Send Email
    try:
        subject = "Your Password Reset Code"
        message = f"Your 6-digit verification code is: {code}\nThis code is valid for 10 minutes."
        send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
        
        # Store email in session for next steps
        request.session['reset_email'] = user.email
        messages.success(request, f"A 6-digit code has been sent to {user.email}")
        return redirect('verify_otp')
    except Exception as e:
        logger.error(f"Error sending email: {type(e).__name__}: {e}")
        messages.error(request, f"Failed to send email. Please try again later.")
        return redirect('password_change')

def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Generate 6-digit OTP
            code = str(random.randint(100000, 999999))
            
            # Save OTP
            OTP.objects.filter(user=user).delete() # Delete old ones
            OTP.objects.create(user=user, code=code)
            
            # Send Email
            try:
                subject = "Your Password Reset Code"
                message = f"Your 6-digit verification code is: {code}\nThis code is valid for 10 minutes."
                send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
                
                # Store email in session for next steps
                request.session['reset_email'] = email
                messages.success(request, f"A 6-digit code has been sent to {email}")
                return redirect('verify_otp')
            except Exception as e:
                import traceback
                print(f"Error sending email: {type(e).__name__}: {e}")
                traceback.print_exc()
                messages.error(request, f"Failed to send email (Error: {type(e).__name__}). Please try again later.")
    else:
        form = ForgotPasswordForm()
    return render(request, 'registration/forgot_password.html', {'form': form})

def verify_otp(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp']
            user = User.objects.get(email=email)
            otp_obj = OTP.objects.filter(user=user, code=otp_code).first()
            
            if otp_obj and otp_obj.is_valid():
                request.session['otp_verified'] = True
                return redirect('reset_password')
            else:
                messages.error(request, "Invalid or expired code.")
    else:
        form = VerifyOTPForm()
    return render(request, 'registration/verify_otp.html', {'form': form})

def reset_password(request):
    email = request.session.get('reset_email')
    otp_verified = request.session.get('otp_verified')
    
    if not email or not otp_verified:
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Cleanup session
            del request.session['reset_email']
            del request.session['otp_verified']
            OTP.objects.filter(user=user).delete()
            
            messages.success(request, "Password has been reset successfully. You can now login.")
            return redirect('login')
    else:
        form = SetPasswordForm()
    return render(request, 'registration/reset_password.html', {'form': form})

class CustomPasswordChangeView(PasswordChangeView):
    def get_form_class(self):
        # Determine if the user needs to set a password (no usable password or social account)
        is_social = False
        try:
            from allauth.socialaccount.models import SocialAccount
            if SocialAccount.objects.filter(user=self.request.user).exists():
                is_social = True
        except ImportError:
            pass

        if not self.request.user.has_usable_password() or is_social:
            return AllauthSetPasswordForm
            
        return super().get_form_class()
import pandas as pd
import requests
import io
import datetime
import math
from decimal import Decimal
from django.db.models import Sum
import xml.etree.ElementTree as ET
from dateutil import parser
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.db.models import Sum, F
from django.db.models.functions import Upper

PORTFOLIO_HEADERS = ['Instrument', 'Quantity', 'Average Cost', 'LTP']
PNL_HEADERS = ['Symbol', 'Quantity', 'Buy Value', 'Sell Value', 'Profit', 'Entry Date', 'Exit Date']

STRATEGY_SYMBOLS = {
    'flexi': {
        'HNGSNGBEES', 'GOLDBEES', 'MON100', 'NIFTYBEES', 'SILVERBEES'
    },
    'quant': {
        'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
        'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BHARTIARTL',
        'CIPLA', 'COALINDIA', 'DRREDDY', 'EICHERMOT', 'ETERNAL',
        'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE', 'HINDALCO',
        'HINDUNILVR', 'ICICIBANK', 'ITC', 'INFY', 'INDIGO',
        'JSWSTEEL', 'JIOFIN', 'KOTAKBANK', 'LT', 'M&M',
        'MARUTI', 'MAXHEALTH', 'NTPC', 'NESTLEIND', 'ONGC',
        'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
        'SUNPHARMA', 'TCS', 'TATACONSUM', 'TMPV', 'TATASTEEL',
        'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
    },
    'pyramid': {
        'HEALTHY', 'BFSI', 'METALIETF', 'HDFCSML250', 'INFRABEES',
        'PHARMABEES', 'JUNIORBEES', 'ALPHA', 'MAFANG', 'MID150BEES',
        'ITBEES', 'MODEFENCE', 'MOVALUE', 'SMALLCAP', 'BANKBEES',
        'OILIETF', 'AUTOIETF', 'MOREALTY', 'CPSEETF', 'PSUBANK',
        'CONSUMBEES', 'LOWVOLIETF', 'MOMENTUM50', 'AXISVALUE', 'HDFCGROWTH'
    }
}

def handle_uploaded_file(f):
    if f.name.endswith('.csv'):
        return pd.read_csv(f)
    elif f.name.endswith('.xlsx'):
        return pd.read_excel(f)
    return None

def clean_numeric(val, to_int=False):
    """
    Clean numeric strings containing commas, currency symbols, and quotes.
    Handles pd.NA/NaN, floats, and ints.
    """
    if pd.isna(val) or val is None:
        return None
    
    if isinstance(val, (int, float)):
        return int(val) if to_int else float(val)
    
    if isinstance(val, str):
        # Remove commas, currency symbols, and various quotes
        cleaned = val.replace(',', '').replace('₹', '').replace('"', '').replace("'", "")
        # Handle smart quotes and other potential non-numeric junk
        cleaned = cleaned.replace('“', '').replace('”', '').replace('‘', '').replace('’', '').strip()
        
        if not cleaned:
            return None
        
        try:
            return int(float(cleaned)) if to_int else float(cleaned)
        except (ValueError, TypeError):
            return None
    return None

# Removed fetch_live_ltp from here as it is now in core.utils

def fetch_market_data():
    """Fetch market ticker data from MarketTicker model."""
    market_list = []
    tickers = MarketTicker.objects.all()
    for t in tickers:
        market_list.append({
            'name': t.name,
            'price': t.price,
            'change': t.change,
            'symbol': t.name.upper().split(' ')[0] # Heuristic: use first word of name as symbol
        })
    return market_list

SHEET_ID = "12eLJHTlHO1naQgJ-dzf-UTgUbasVv02tgwlHKofG2Y4"

STRATEGY_SHEET_TABS = {
    'flexi': 'FlexiMultiInvest',
    'quant': 'NiftyQuant',
    'pyramid': 'Pyramiding',
    'growth': 'ReinvestX',
}



def fetch_rss_feed(url, source_name, timeout=10):
    """Generic RSS fetcher with source-specific handling."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Handle potential encoding issues
        response.encoding = 'utf-8'
        
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall('.//item'):
            try:
                title_node = item.find('title')
                link_node = item.find('link')
                pub_date_node = item.find('pubDate')
                
                title = title_node.text if title_node is not None else "No Title"
                link = link_node.text if link_node is not None else "#"
                pub_date_str = pub_date_node.text if pub_date_node is not None else ""
                
                description_node = item.find('description')
                description = description_node.text if description_node is not None else ""
                if description:
                    import re
                    description = re.sub('<[^<]+?>', '', description)
                
                items.append({
                    'source': source_name,
                    'title': title,
                    'link': link,
                    'pub_date': pub_date_str,
                    'description': description[:150] + "..." if len(description or "") > 150 else (description or "")
                })
            except Exception as e:
                print(f"Error parsing item in {source_name}: {e}")
                continue
        return items
    except Exception as e:
        print(f"Error fetching {source_name} feed: {e}")
        return []

def fetch_landing_data():
    """Fetch all RSS feeds for the landing page with caching."""
    cache_key = 'landing_rss_data_v3'  # v3: Livemint + Zerodha Pulse
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    # Left tile: Livemint Markets RSS
    nse_news = fetch_rss_feed('https://www.livemint.com/rss/markets', 'Livemint')
    
    # Financial News - Zerodha Pulse
    pulse_news = fetch_rss_feed('http://pulse.zerodha.com/feed.php', 'Zerodha Pulse')
    
    result = {
        'nse_news': nse_news[:20],
        'financial_news': pulse_news[:20]
    }
    
    if nse_news or pulse_news:
        cache.set(cache_key, result, 1800) # 30 mins
    return result

@ensure_csrf_cookie
def landing(request):
    """Public landing page with marketing content and ticker."""
    market_data = fetch_market_data()
    landing_data = fetch_landing_data()
    context = {
        'market_data': market_data,
        'nse_news': landing_data.get('nse_news', []),
        'financial_news': landing_data.get('financial_news', []),
        'last_updated': datetime.datetime.now(),
    }
    return render(request, 'core/landing.html', context)

@ensure_csrf_cookie
def strategy(request):
    """Investment strategy detail page with recommended stocks from Google Sheets."""
    strategy_stocks = fetch_strategy_stocks()
    
    # Identify "Others" stocks for the current user and calculate allocation
    others_stocks = []
    allocation_data = {
        'FlexiMultiInvest': 0,
        'NiftyQuant': 0,
        'Pyramiding': 0,
        'ReinvestX': 0,
        'Others': 0
    }
    
    if request.user.is_authenticated:
        # Get all symbols from strategy marquees
        all_strategy_symbols = set()
        symbol_to_strategy = {}
        
        # Map internal keys to display names for the graph
        strategy_labels = {
            'flexi': 'FlexiMultiInvest',
            'quant': 'NiftyQuant',
            'pyramid': 'Pyramiding',
            'growth': 'ReinvestX'
        }
        
        for s_key, s_list in strategy_stocks.items():
            for sym in s_list:
                sym_upper = sym.upper()
                all_strategy_symbols.add(sym_upper)
                symbol_to_strategy[sym_upper] = s_key
        
        # Get user's active portfolio
        portfolio_items = Portfolio.objects.filter(
            user=request.user, 
            quantity__gt=0
        ).select_related('instrument')
        
        user_portfolio_symbols = set()
        for item in portfolio_items:
            symbol = item.instrument.symbol.upper()
            user_portfolio_symbols.add(symbol)
            
            # Use invested_amount property from Portfolio model
            invested = float(item.invested_amount)
            
            s_key = symbol_to_strategy.get(symbol)
            if s_key in strategy_labels:
                allocation_data[strategy_labels[s_key]] += invested
            else:
                allocation_data['Others'] += invested
        
        # Others list for marquee = Portfolio stocks not in any strategy marquee
        others_stocks = sorted(list(user_portfolio_symbols - all_strategy_symbols))

    # Prepare labels and data for Chart.js
    chart_labels = list(allocation_data.keys())
    chart_values = list(allocation_data.values())
    has_investments = sum(chart_values) > 0

    context = {
        'flexi_stocks': strategy_stocks.get('flexi', []),
        'quant_stocks': strategy_stocks.get('quant', []),
        'pyramid_stocks': strategy_stocks.get('pyramid', []),
        'growth_stocks': strategy_stocks.get('growth', []),
        'others_stocks': others_stocks,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'has_investments': has_investments,
    }
    return render(request, 'core/strategy.html', context)

def mf_guide(request):
    """Mutual Fund Guide page - redirects authenticated users to dashboard."""
    if request.user.is_authenticated:
        return redirect('mf_dashboard')
    return render(request, 'core/mf_guide.html')

@login_required
def mf_dashboard(request):
    """Isolated dashboard for Mutual Funds."""
    all_holdings = MFPortfolio.objects.filter(user=request.user).select_related('fund')
    
    total_invested = sum(h.invested_amount for h in all_holdings)
    total_current_value = sum(h.current_value for h in all_holdings)
    total_unrealized_pnl = total_current_value - total_invested
    total_realized_profit = sum(h.realized_profit for h in all_holdings)
    total_day_change = sum(h.day_change for h in all_holdings)
    
    total_pnl_pct = 0
    if total_invested > 0:
        total_pnl_pct = (total_unrealized_pnl / total_invested) * 100
        
    # Only display holdings with units > 0
    mf_holdings = [h for h in all_holdings if h.units > 0]
    
    # Process advice for each holding
    for h in mf_holdings:
        h.advice = []
        if h.pnl_percentage >= 22:
            h.advice.append({'type': 'SELL', 'reason': f'Target 22% reached ({float(h.pnl_percentage):.2f}%)'})
        
        if h.realized_profit > 0:
            target = Decimal('100000') + h.realized_profit
            if h.invested_amount < target:
                gap = target - h.invested_amount
                h.advice.append({'type': 'BUY', 'reason': f'Realized profit target ₹{float(gap):,.0f} gap'})

    context = {
        'mf_holdings': mf_holdings,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_realized_profit': total_realized_profit,
        'total_day_change': total_day_change,
        'total_pnl_pct': total_pnl_pct,
        'last_updated': timezone.now(),
    }
    return render(request, 'core/mf_dashboard.html', context)

@login_required
def add_mf_portfolio(request):
    """Add a mutual fund holding manually."""
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').strip().upper()
        
        try:
            units = Decimal(request.POST.get('units', '0'))
            avg_nav = Decimal(request.POST.get('avg_nav', '0'))
            realized_profit = Decimal(request.POST.get('realized_profit', '0'))
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric values provided.")
            return redirect('mf_dashboard')

        if not symbol or units < 0 or avg_nav < 0:
            messages.error(request, "Please provide valid symbol, units, and average NAV.")
            return redirect('mf_dashboard')
            
        # Try to find or create MutualFund
        fund, created = MutualFund.objects.get_or_create(symbol=symbol)
        if created or fund.nav == 0:
            # Try to fetch initial NAV
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                info = ticker.info
                nav_val = info.get('regularMarketPrice') or info.get('navPrice') or info.get('previousClose')
                if nav_val:
                    fund.nav = Decimal(str(nav_val))
                else:
                    fund.nav = avg_nav # Fallback to avg_nav
                fund.name = info.get('longName') or symbol
                fund.save()
            except Exception as e:
                logger.error(f"Error fetching NAV for {symbol}: {e}")
                if created: 
                    fund.name = symbol
                    fund.nav = avg_nav
                    fund.save()

        # Update or create MFPortfolio item
        portfolio_item, p_created = MFPortfolio.objects.get_or_create(
            user=request.user, fund=fund,
            defaults={'units': units, 'avg_nav': avg_nav, 'realized_profit': realized_profit}
        )
        if not p_created:
            if units > 0:
                # Weighted average calculation
                total_units = portfolio_item.units + units
                new_avg_nav = ((portfolio_item.units * portfolio_item.avg_nav) + (units * avg_nav)) / total_units
                portfolio_item.units = total_units
                portfolio_item.avg_nav = new_avg_nav
            
            # Add to realized profit if provided (don't overwrite existing with 0)
            if realized_profit != 0:
                portfolio_item.realized_profit += realized_profit
            portfolio_item.save()
            
        # Record transaction if units > 0
        if units > 0:
            MFTransaction.objects.create(
                user=request.user,
                fund=fund,
                transaction_type='BUY',
                units=units,
                remaining_units=units,
                price=avg_nav,
                date=timezone.now().date()
            )
            
        messages.success(request, f"Successfully added {fund.name} to your Mutual Fund portfolio.")
        return redirect('mf_dashboard')
        
    prefill_symbol = request.GET.get('symbol', '')
    return render(request, 'core/mf_add_item.html', {'prefill_symbol': prefill_symbol})

@login_required
def sell_mf_portfolio(request, pk):
    holding = get_object_or_404(MFPortfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            units_to_sell = Decimal(request.POST.get('units', '0'))
            sell_price = Decimal(request.POST.get('price', '0'))
            sell_date_str = request.POST.get('date')
            sell_date = pd.to_datetime(sell_date_str).date() if sell_date_str else timezone.now().date()
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric values provided.")
            return redirect('mf_dashboard')

        if units_to_sell <= 0:
            messages.error(request, "Units to sell must be greater than zero.")
            return redirect('mf_dashboard')

        if units_to_sell > holding.units:
            messages.error(request, f"Insufficient units. You only have {holding.units} units.")
            return redirect('mf_dashboard')
            
        # FIFO Calculation: Find buy lots for this user and fund
        buy_lots = MFTransaction.objects.filter(
            user=request.user,
            fund=holding.fund,
            transaction_type='BUY',
            remaining_units__gt=0
        ).order_by('date', 'created_at')
        
        remaining_to_sell = units_to_sell
        total_cost = Decimal('0')
        
        for lot in buy_lots:
            if remaining_to_sell <= 0:
                break
            
            units_from_lot = min(lot.remaining_units, remaining_to_sell)
            total_cost += units_from_lot * lot.price
            
            lot.remaining_units -= units_from_lot
            lot.save()
            
            remaining_to_sell -= units_from_lot
            
        sell_value = units_to_sell * sell_price
        profit = sell_value - total_cost
        
        # Update Portfolio
        holding.units -= units_to_sell
        holding.realized_profit += profit
        
        # Recalculate Avg NAV based on remaining lots
        remaining_lots = MFTransaction.objects.filter(
            user=request.user,
            fund=holding.fund,
            transaction_type='BUY',
            remaining_units__gt=0
        )
        total_rem_units = sum(l.remaining_units for l in remaining_lots)
        total_rem_cost = sum(l.remaining_units * l.price for l in remaining_lots)
        
        if total_rem_units > 0:
            holding.avg_nav = total_rem_cost / total_rem_units
        else:
            # If all sold, we can either keep the last avg_nav or reset to 0. 
            # Usually, keeping it is fine, but since units are 0, it doesn't matter for valuation.
            pass
            
        holding.save()
        
        # Record Transaction
        MFTransaction.objects.create(
            user=request.user,
            fund=holding.fund,
            transaction_type='SELL',
            units=units_to_sell,
            price=sell_price,
            date=sell_date
        )
        
        messages.success(request, f"Sold {units_to_sell} units of {holding.fund.name} at {sell_price}. Profit: ₹{float(profit):,.2f}")
        return redirect('mf_dashboard')
        
    return render(request, 'core/mf_sell_item.html', {'holding': holding})

@login_required
def delete_mf_portfolio(request, pk):
    holding = get_object_or_404(MFPortfolio, pk=pk, user=request.user)
    fund_name = holding.fund.name
    holding.delete()
    messages.success(request, f"Removed {fund_name} from your portfolio.")
    return redirect('mf_dashboard')

@login_required
def mf_transaction_history(request):
    transactions = MFTransaction.objects.filter(user=request.user).select_related('fund').order_by('-date', '-created_at')
    return render(request, 'core/mf_transactions.html', {'transactions': transactions})

@login_required
def refresh_mf_navs(request):
    """Fetch latest NAVs for all funds in the user's portfolio."""
    mf_holdings = MFPortfolio.objects.filter(user=request.user).select_related('fund')
    if not mf_holdings:
        return redirect('mf_dashboard')
    
    import yfinance as yf
    symbols = [h.fund.symbol for h in mf_holdings]
    
    try:
        # Fetch data for all symbols at once
        if len(symbols) == 1:
            ticker = yf.Ticker(symbols[0])
            hist = ticker.history(period="1d")
            if not hist.empty:
                new_nav = hist['Close'].iloc[-1]
                fund = mf_holdings[0].fund
                fund.prev_nav = fund.nav # Store old NAV
                fund.nav = Decimal(str(new_nav))
                fund.save()
        else:
            data = yf.download(symbols, period="1d", progress=False)
            # Handle the case where download returns a multi-index or single Series
            close_data = data['Close']
            for h in mf_holdings:
                try:
                    sym = h.fund.symbol
                    if sym in close_data.columns:
                        val = close_data[sym].iloc[-1]
                        if not pd.isna(val):
                            h.fund.prev_nav = h.fund.nav # Store old NAV
                            h.fund.nav = Decimal(str(val))
                            h.fund.save()
                except Exception: continue
                
        messages.success(request, "Mutual Fund NAVs refreshed successfully.")
    except Exception as e:
        logger.error(f"NAV Refresh failed: {e}")
        messages.error(request, "Failed to refresh some NAVs. Yahoo Finance might be temporarily unavailable.")
        
    return redirect('mf_dashboard')

# --- COIN (Crypto) Module ---

@login_required
def coin_dashboard(request):
    """Dashboard for Cryptocurrency holdings using FIFO."""
    all_holdings = CoinPortfolio.objects.filter(user=request.user).select_related('coin')
    
    total_invested = sum(h.invested_amount for h in all_holdings)
    total_current_value = sum(h.current_value for h in all_holdings)
    total_unrealized_pnl = total_current_value - total_invested
    total_realized_profit = sum(h.realized_profit for h in all_holdings)
    total_day_change = sum(h.day_change for h in all_holdings)
    
    total_pnl_pct = 0
    if total_invested > 0:
        total_pnl_pct = (total_unrealized_pnl / total_invested) * 100
        
    # Only display holdings with units > 0
    coin_holdings = [h for h in all_holdings if h.units > 0]
    
    context = {
        'coin_holdings': coin_holdings,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_realized_profit': total_realized_profit,
        'total_day_change': total_day_change,
        'total_pnl_pct': total_pnl_pct,
        'last_updated': timezone.now(),
    }
    return render(request, 'core/coin_dashboard.html', context)

@login_required
def add_coin(request):
    """Add a cryptocurrency holding manually."""
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').strip().upper()
        # Ensure Crypto-INR symbol style if not provided (e.g. BTC -> BTC-INR)
        if '-' not in symbol and not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            symbol = f"{symbol}-INR"
            
        try:
            units = Decimal(request.POST.get('units', '0'))
            avg_price = Decimal(request.POST.get('avg_price', '0'))
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric values provided.")
            return redirect('coin_dashboard')

        if not symbol or units <= 0 or avg_price <= 0:
            messages.error(request, "Please provide valid symbol, units, and average price.")
            return redirect('coin_dashboard')
            
        coin, created = Coin.objects.get_or_create(symbol=symbol)
        if created or coin.price == 0:
            try:
                import requests
                headers = {'User-Agent': 'Mozilla/5.0'}
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                response = requests.get(url, headers=headers, timeout=5)
                data = response.json()
                price_val = data['chart']['result'][0]['meta']['regularMarketPrice']
                
                if price_val:
                    coin.price = Decimal(str(price_val))
                else:
                    coin.price = avg_price
                    
                # Try to get a nicer name, fallback to symbol
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    coin.name = info.get('shortName') or info.get('longName') or symbol
                except Exception:
                    coin.name = symbol
                    
                coin.save()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error fetching price for {symbol}: {e}")
                if created: 
                    coin.name = symbol
                    coin.price = avg_price
                    coin.save()

        holding, h_created = CoinPortfolio.objects.get_or_create(
            user=request.user, 
            coin=coin,
            defaults={'units': 0, 'avg_price': 0}
        )
        
        # Update Portfolio with weighted average for the main display (though we use FIFO for sells)
        total_units = holding.units + units
        total_cost = (holding.units * holding.avg_price) + (units * avg_price)
        holding.units = total_units
        holding.avg_price = total_cost / total_units if total_units > 0 else 0
        holding.save()

        # Record Transaction for FIFO
        CoinTransaction.objects.create(
            user=request.user,
            coin=coin,
            transaction_type='BUY',
            units=units,
            remaining_units=units,
            price=avg_price,
            date=timezone.now().date()
        )
        
        messages.success(request, f"Added {units} units of {coin.name} to your portfolio.")
        return redirect('coin_dashboard')
        
    return render(request, 'core/coin_add_item.html')

@login_required
def sell_coin(request, pk):
    """Sell a cryptocurrency holding using FIFO."""
    holding = get_object_or_404(CoinPortfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            units_to_sell = Decimal(request.POST.get('units', '0'))
            sell_price = Decimal(request.POST.get('price', '0'))
            sell_date_str = request.POST.get('date')
            sell_date = pd.to_datetime(sell_date_str).date() if sell_date_str else timezone.now().date()
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric values provided.")
            return redirect('coin_dashboard')

        if units_to_sell <= 0:
            messages.error(request, "Units to sell must be greater than zero.")
            return redirect('coin_dashboard')

        if units_to_sell > holding.units:
            messages.error(request, f"Insufficient units. You only have {holding.units} units.")
            return redirect('coin_dashboard')
            
        # FIFO Calculation
        buy_lots = CoinTransaction.objects.filter(
            user=request.user,
            coin=holding.coin,
            transaction_type='BUY',
            remaining_units__gt=0
        ).order_by('date', 'created_at')
        
        remaining_to_sell = units_to_sell
        total_cost = Decimal('0')
        
        for lot in buy_lots:
            if remaining_to_sell <= 0:
                break
            
            units_from_lot = min(lot.remaining_units, remaining_to_sell)
            total_cost += units_from_lot * lot.price
            
            lot.remaining_units -= units_from_lot
            lot.save()
            
            remaining_to_sell -= units_from_lot
            
        sell_value = units_to_sell * sell_price
        profit = sell_value - total_cost
        
        # Update Portfolio
        holding.units -= units_to_sell
        holding.realized_profit += profit
        
        # Recalculate Avg Price based on remaining lots
        remaining_lots = CoinTransaction.objects.filter(
            user=request.user,
            coin=holding.coin,
            transaction_type='BUY',
            remaining_units__gt=0
        )
        total_rem_units = sum(l.remaining_units for l in remaining_lots)
        total_rem_cost = sum(l.remaining_units * l.price for l in remaining_lots)
        
        if total_rem_units > 0:
            holding.avg_price = total_rem_cost / total_rem_units
            
        holding.save()
        
        # Record Transaction
        CoinTransaction.objects.create(
            user=request.user,
            coin=holding.coin,
            transaction_type='SELL',
            units=units_to_sell,
            price=sell_price,
            date=sell_date
        )
        
        messages.success(request, f"Sold {units_to_sell} units of {holding.coin.name} at {sell_price}. Profit: ₹{float(profit):,.2f}")
        return redirect('coin_dashboard')
        
    return render(request, 'core/coin_sell_item.html', {'holding': holding})

@login_required
def delete_coin_portfolio(request, pk):
    holding = get_object_or_404(CoinPortfolio, pk=pk, user=request.user)
    coin_name = holding.coin.name
    holding.delete()
    messages.success(request, f"Removed {coin_name} from your portfolio.")
    return redirect('coin_dashboard')

@login_required
def coin_transaction_history(request):
    transactions = CoinTransaction.objects.filter(user=request.user).select_related('coin').order_by('-date', '-created_at')
    return render(request, 'core/coin_transactions.html', {'transactions': transactions})

@login_required
def refresh_coin_prices(request):
    """Fetch latest prices for all crypto coins in the user's portfolio."""
    coin_holdings = CoinPortfolio.objects.filter(user=request.user).select_related('coin')
    if not coin_holdings:
        return redirect('coin_dashboard')
    
    import requests
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    success_count = 0
    symbols = list(set([h.coin.symbol for h in coin_holdings]))
    
    try:
        for symbol in symbols:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            try:
                response = requests.get(url, headers=headers, timeout=5)
                data = response.json()
                price_val = data['chart']['result'][0]['meta']['regularMarketPrice']
                
                if price_val:
                    for h in coin_holdings:
                        if h.coin.symbol == symbol:
                            h.coin.prev_price = h.coin.price
                            h.coin.price = Decimal(str(price_val))
                            h.coin.save()
                            success_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Direct request failed for {symbol}: {e}")
                
        if success_count > 0:
            messages.success(request, "Coin prices refreshed successfully.")
        else:
            messages.error(request, "Failed to refresh some prices.")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Coin Price Refresh failed: {e}")
        messages.error(request, "Failed to refresh some prices.")
        
    return redirect('coin_dashboard')

@login_required
def portfolio(request):
    """Unified Portfolio Dashboard."""
    # 1. Stocks/ETF
    recommendations, realized_profits, _ = get_recommendations(request.user)
    stocks_recs = [r for r in recommendations if r.get('in_portfolio', False)]
    stocks_invested = float(sum(r.get('invested_amount', 0) for r in stocks_recs))
    stocks_current = float(sum(r.get('current_value', 0) for r in stocks_recs))
    stocks_unrealized = stocks_current - stocks_invested
    stocks_realized = float(sum(realized_profits.values()) if isinstance(realized_profits, dict) else 0)

    # 2. Mutual Funds
    mf_holdings = MFPortfolio.objects.filter(user=request.user).select_related('fund')
    mf_invested = float(sum(h.invested_amount for h in mf_holdings))
    mf_current = float(sum(h.current_value for h in mf_holdings))
    mf_unrealized = mf_current - mf_invested
    mf_realized = float(sum(h.realized_profit for h in mf_holdings))

    # 3. Coin (Crypto)
    coin_holdings = CoinPortfolio.objects.filter(user=request.user).select_related('coin')
    coin_invested = float(sum(h.invested_amount for h in coin_holdings))
    coin_current = float(sum(h.current_value for h in coin_holdings))
    coin_unrealized = coin_current - coin_invested
    coin_realized = float(sum(h.realized_profit for h in coin_holdings))

    # 4. NPS
    nps_holdings = NPSPortfolio.objects.filter(user=request.user).select_related('fund')
    nps_invested = float(sum(h.invested_amount for h in nps_holdings))
    nps_current = float(sum(h.current_value for h in nps_holdings))
    nps_unrealized = nps_current - nps_invested
    nps_realized = float(sum(h.realized_profit for h in nps_holdings))

    # 5. Fixed Assets
    fd_invested = fd_current = fd_unrealized = fd_percentage = 0.0
    try:
        fd_holdings = FixedAsset.objects.filter(user=request.user)
        fd_invested = float(sum(h.invested_amount for h in fd_holdings))
        fd_current = float(sum(h.current_value for h in fd_holdings))
        fd_unrealized = float(sum(h.unrealized_pnl for h in fd_holdings))
        if fd_invested > 0:
            fd_percentage = (fd_unrealized / fd_invested) * 100
    except Exception:
        pass

    # 6. Other Assets (Real Estate, Gold, etc)
    other_invested = other_current = other_unrealized = other_percentage = 0.0
    try:
        other_holdings = OtherAsset.objects.filter(user=request.user)
        other_invested = float(sum(h.purchase_price for h in other_holdings))
        other_current = float(sum(h.current_value for h in other_holdings))
        other_unrealized = float(sum(h.unrealized_pnl for h in other_holdings))
        if other_invested > 0:
            other_percentage = (other_unrealized / other_invested) * 100
    except Exception:
        pass

    # 7. Loans
    loans = Loan.objects.filter(user=request.user, is_active=True)
    for l in loans:
        _process_auto_emis(l)
    
    loan_taken = float(sum(l.loan_amount for l in loans))
    loan_outstanding = float(sum(l.current_outstanding for l in loans))
    
    # Calculate upcoming EMIs (due in next 7 days)
    from datetime import timedelta
    next_week = timezone.now().date() + timedelta(days=7)
    upcoming_emis_count = loans.filter(next_emi_date__lte=next_week, next_emi_date__isnull=False).count()

    # Calculate Totals
    total_investment_cost = stocks_invested + mf_invested + coin_invested + nps_invested + fd_invested + other_invested
    # USER REQUEST: Deduct loan outstanding from Current Value
    total_latest_value = (stocks_current + mf_current + coin_current + nps_current + fd_current + other_current) - loan_outstanding
    total_unrealized_gain = total_latest_value + loan_outstanding - total_investment_cost
    total_realized_gain = stocks_realized + mf_realized + coin_realized + nps_realized
    total_other_gain = 0  # Placeholder for future models

    context = {
        'total_investment_cost': total_investment_cost,
        'total_latest_value': total_latest_value,
        'total_unrealized_gain': total_unrealized_gain,
        'total_realized_gain': total_realized_gain,
        'total_other_gain': total_other_gain,

        'stocks_invested': stocks_invested,
        'stocks_current': stocks_current,
        'stocks_unrealized': stocks_unrealized,
        'stocks_realized': stocks_realized,

        'mf_invested': mf_invested,
        'mf_current': mf_current,
        'mf_unrealized': mf_unrealized,
        'mf_realized': mf_realized,

        'coin_invested': coin_invested,
        'coin_current': coin_current,
        'coin_unrealized': coin_unrealized,
        'coin_realized': coin_realized,

        'nps_invested': nps_invested,
        'nps_current': nps_current,
        'nps_unrealized': nps_unrealized,
        'nps_realized': nps_realized,

        'fd_invested': fd_invested,
        'fd_current': fd_current,
        'fd_unrealized': fd_unrealized,
        'fd_percentage': fd_percentage,

        'other_invested': other_invested,
        'other_current': other_current,
        'other_unrealized': other_unrealized,
        'other_percentage': other_percentage,

        'loan_taken': loan_taken,
        'loan_outstanding': loan_outstanding,
        'upcoming_emis_count': upcoming_emis_count,
        
        # Actionable Signals Placeholders
        'mf_buy_count': 0,
        'mf_redemption_count': 0,
        'coin_buy_count': 0,
        'coin_sell_count': 0,
    }
    return render(request, 'core/portfolio.html', context)
def etf_guide(request):
    """ETF Guide page."""
    return render(request, 'core/etf_guide.html')

def nps_guide(request):
    """NPS Guide page."""
    return render(request, 'core/nps_guide.html')

def donation(request):
    """Donation page."""
    return render(request, 'core/donation.html')

def about_project(request):
    """Project Report Page."""
    return render(request, 'core/about_project.html')

@login_required
def dashboard(request):
    recommendations, realized_profits, strategy_stocks = get_recommendations(request.user)
    
    total_invested = 0
    total_current_value = 0
    total_unrealized_pnl = 0
        
    total_realized_profit = sum(realized_profits.values())

    # Strategy-based Filtering
    all_strategy_stocks = fetch_strategy_stocks()
    current_strategy = request.GET.get('strategy')
    
    # Flatten all strategy symbols for easy lookup
    all_known_strategy_symbols = set()
    for s_list in all_strategy_stocks.values():
        all_known_strategy_symbols.update(s_list)
    
    # Filter recommendations based on current strategy
    if current_strategy:
        filtered_recommendations = []
        if current_strategy == 'others':
            # Show only stocks NOT in any strategy list
            for r in recommendations:
                if r['symbol'].upper() not in all_known_strategy_symbols:
                    filtered_recommendations.append(r)
        else:
            # Show only stocks in the specific strategy list
            target_list = all_strategy_stocks.get(current_strategy, [])
            for r in recommendations:
                if r['symbol'].upper() in target_list:
                    filtered_recommendations.append(r)
        recommendations = filtered_recommendations
    else:
        # Default view: show portfolio items PLUS all strategy signals
        recommendations = [
            r for r in recommendations 
            if r.get('in_portfolio', False) or r.get('action') in ['BUY', 'SELL', 'REDUCE']
        ]

    # Recalculate totals based on the filtered view
    total_invested = sum(r['invested_amount'] for r in recommendations)
    total_current_value = sum(r['current_value'] for r in recommendations)
    total_unrealized_pnl = sum(r['unrealized_pnl'] for r in recommendations)
    
    total_unrealized_pnl_percent = 0
    if total_invested > 0:
        total_unrealized_pnl_percent = (total_unrealized_pnl / total_invested) * 100
    
    total_day_change = sum(r.get('day_change', 0) for r in recommendations if r.get('in_portfolio'))
    total_day_change_percent = 0
    previous_total_value = total_current_value - total_day_change
    if previous_total_value > 0:
        total_day_change_percent = (total_day_change / previous_total_value) * 100

    if current_strategy and current_strategy != 'others':
        target_list = all_strategy_stocks.get(current_strategy, [])
        total_realized_profit = sum(profit for symbol, profit in realized_profits.items() if symbol.upper() in target_list)
    elif current_strategy == 'others':
        total_realized_profit = sum(profit for symbol, profit in realized_profits.items() if symbol.upper() not in all_known_strategy_symbols)
    else:
        total_realized_profit = sum(realized_profits.values())
        


    # 1. Sell Recommendations: Only SELL actions, sorted by P&L value (unrealized_pnl) desc
    sell_recommendations = [r for r in recommendations if r['action'] == 'SELL']
    sell_recommendations.sort(key=lambda x: x['unrealized_pnl'], reverse=True)

    # 2. Buy Recommendations: Only BUY actions, sorted by buy_gap desc
    buy_recommendations = [r for r in recommendations if r['action'] == 'BUY']
    buy_recommendations.sort(key=lambda x: x['buy_gap'], reverse=True)

    # 3. Reduce Recommendations: Only REDUCE actions, sorted by reduce_gap desc
    reduce_sigs = [r for r in recommendations if r['action'] == 'REDUCE']
    reduce_sigs.sort(key=lambda x: x['reduce_gap'], reverse=True)

    from .models import Strategy, MarketTicker
    last_strategy_update = Strategy.objects.aggregate(models.Max('updated_at'))['updated_at__max']
    last_ticker_update = MarketTicker.objects.aggregate(models.Max('updated_at'))['updated_at__max']
    
    # Get the most recent of the two
    last_updated = last_strategy_update
    if last_ticker_update and (not last_updated or last_ticker_update > last_updated):
        last_updated = last_ticker_update
    
    if not last_updated:
        last_updated = datetime.datetime.now()

    context = {
        'recommendations': recommendations,
        'sell_recommendations': sell_recommendations,
        'buy_recommendations': buy_recommendations,
        'reduce_sigs': reduce_sigs,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_unrealized_pnl_percent': total_unrealized_pnl_percent,
        'total_realized_profit': total_realized_profit,
        'total_day_change': total_day_change,
        'total_day_change_percent': total_day_change_percent,
        'last_updated': last_updated,
        'current_strategy': current_strategy,
    }
    return render(request, 'core/dashboard.html', context)

def search_instruments(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    instruments = Instrument.objects.filter(
        is_verified=True
    ).filter(
        models.Q(name__icontains=query) | models.Q(symbol__icontains=query)
    )[:10]
    
    results = [
        {'id': inst.id, 'name': inst.name, 'symbol': inst.symbol, 'ltp': float(inst.last_price or 0)}
        for inst in instruments
    ]
    return JsonResponse(results, safe=False)

@login_required
def add_portfolio_item(request):
    if request.method == 'POST':
        form = ManualPortfolioForm(request.POST)
        if form.is_valid():
            symbol = form.cleaned_data['symbol'].strip().upper()
            quantity = form.cleaned_data['quantity']
            avg_cost = form.cleaned_data['avg_cost']
            transaction_date = form.cleaned_data.get('date') or timezone.now().date()

            # Get Instrument (must be verified)
            try:
                inst = Instrument.objects.get(symbol__iexact=symbol, is_verified=True)
            except Instrument.DoesNotExist:
                messages.error(request, f"'{symbol}' is not a verified instrument in our database.")
                return render(request, 'core/add_portfolio.html', {'form': form, 'title': 'Add Stock Manually'})

            # Try to get initial LTP from live data if possible
            live_ltps = fetch_live_ltp()
            ltp_data = live_ltps.get(symbol)
            if isinstance(ltp_data, tuple):
                ltp = ltp_data[0]
            else:
                ltp = ltp_data or avg_cost

            # Create Transaction record
            Transaction.objects.create(
                user=request.user,
                instrument=inst,
                transaction_type='BUY',
                quantity=quantity,
                remaining_quantity=quantity,
                price=avg_cost,
                date=transaction_date
            )

            portfolio, created = Portfolio.objects.get_or_create(
                user=request.user, 
                instrument=inst,
                defaults={'quantity': 0, 'avg_cost': Decimal('0'), 'ltp': ltp}
            )
            
            # Update Weighted Average Cost for Portfolio summary
            current_total_cost = Decimal(str(portfolio.quantity)) * portfolio.avg_cost
            new_total_cost = Decimal(str(quantity)) * Decimal(str(avg_cost))
            total_quantity = portfolio.quantity + quantity
            
            new_avg_cost = (current_total_cost + new_total_cost) / Decimal(str(total_quantity))
            
            portfolio.quantity = total_quantity
            portfolio.avg_cost = new_avg_cost
            # Only update LTP if it was 0 or just created
            if created or not portfolio.ltp or portfolio.ltp == 0:
                portfolio.ltp = ltp
            portfolio.save()
            messages.success(request, f"Successfully added/updated {symbol} in your portfolio.")
            return redirect('dashboard')
    else:
        form = ManualPortfolioForm()
    return render(request, 'core/add_portfolio.html', {'form': form, 'title': 'Add Stock Manually'})

@login_required
def upload_portfolio(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = handle_uploaded_file(request.FILES['file'])
            if df is not None:
                # Strict Header Validation
                uploaded_headers = list(df.columns)
                if uploaded_headers != PORTFOLIO_HEADERS:
                    messages.error(request, f"Header mismatch. Expected: {PORTFOLIO_HEADERS}. Got: {uploaded_headers}")
                    return redirect('upload_portfolio')

                try:
                    # Fetch live LTPs to prefer over file data if available
                    live_ltps = fetch_live_ltp()
                    
                    # Track aggregated data per symbol: {symbol: {'qty': total_qty, 'cost': weighted_avg_cost, 'ltp': last_ltp, 'instrument': inst_obj}}
                    aggregated_data = {}

                    for idx, row in df.iterrows():
                        symbol = row.get('Instrument')
                        if not symbol:
                            continue
                        
                        clean_symbol = symbol.strip().upper()
                        qty    = clean_numeric(row.get('Quantity'), to_int=True)
                        avg    = clean_numeric(row.get('Average Cost'))
                        
                        # Prefer Live LTP if available, otherwise fallback to file LTP
                        ltp_data = live_ltps.get(clean_symbol)
                        if isinstance(ltp_data, tuple):
                            ltp = float(ltp_data[0])
                        else:
                            ltp = float(ltp_data or clean_numeric(row.get('LTP')) or 0)

                        # Skip rows where symbol or quantity is missing/NaN
                        if not clean_symbol or (isinstance(clean_symbol, float) and math.isnan(clean_symbol)):
                            continue
                        if qty is None or (isinstance(qty, float) and math.isnan(qty)):
                            continue

                        # Get Instrument (must be verified)
                        from core.utils import resolve_instrument
                        inst = resolve_instrument(clean_symbol)
                        if not inst:
                            messages.warning(request, f"Skipped '{symbol}': Not in verified database.")
                            continue

                        # Create Transaction record for each row (lot preservation)
                        Transaction.objects.create(
                            user=request.user,
                            instrument=inst,
                            transaction_type='BUY',
                            quantity=qty,
                            remaining_quantity=qty,
                            price=avg,
                            date=timezone.now().date()
                        )

                        # Aggregate data for Portfolio update
                        if clean_symbol not in aggregated_data:
                            aggregated_data[clean_symbol] = {
                                'qty': qty,
                                'total_cost': Decimal(str(qty)) * Decimal(str(avg)),
                                'ltp': ltp,
                                'instrument': inst
                            }
                        else:
                            aggregated_data[clean_symbol]['qty'] += qty
                            aggregated_data[clean_symbol]['total_cost'] += Decimal(str(qty)) * Decimal(str(avg))
                            # Update LTP only if we have a non-zero one
                            if ltp > 0:
                                aggregated_data[clean_symbol]['ltp'] = ltp

                    # Update Portfolio once per symbol with aggregated totals
                    for symbol, data in aggregated_data.items():
                        qty = data['qty']
                        total_cost = data['total_cost']
                        avg_cost = total_cost / Decimal(str(qty)) if qty > 0 else 0
                        ltp = data['ltp']
                        inst = data['instrument']

                        portfolio, created = Portfolio.objects.get_or_create(
                            user=request.user,
                            instrument=inst,
                            defaults={
                                'quantity': qty,
                                'avg_cost': avg_cost,
                                'ltp': ltp or 0
                            }
                        )
                        if not created:
                            # If it already exists, we replace with the new upload state (which seems to be the intended behavior of upload_portfolio)
                            portfolio.quantity = qty
                            portfolio.avg_cost = avg_cost
                            # Only update LTP if it was 0 or just provided
                            if not portfolio.ltp or portfolio.ltp == 0 or ltp > 0:
                                portfolio.ltp = ltp or portfolio.ltp
                            portfolio.save()

                    messages.success(request, "Portfolio uploaded successfully.")
                    return redirect('dashboard')
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f"Upload failed: {type(e).__name__}: {e}")
            else:
                messages.error(request, "Invalid file format. Please upload a .csv or .xlsx file.")
    else:
        form = UploadFileForm()
    return render(request, 'core/upload.html', {'form': form, 'title': 'Upload Portfolio'})

@login_required
def export_portfolio(request):
    """Export the user's portfolio data to an Excel file."""
    from django.http import HttpResponse
    import io
    try:
        recommendations, realized_profits, strategy_stocks = get_recommendations(request.user)
        
        # Filter to show only portfolio items (same as dashboard default view)
        recommendations = [
            r for r in recommendations
            if r.get('in_portfolio', False) or (r.get('action') == 'BUY' and r.get('realized_profit', 0) > 0)
        ]

        # Build rows for export
        rows = []
        for r in recommendations:
            rows.append({
                'Instrument': r.get('name', r.get('symbol', '')),
                'Symbol': r.get('symbol', ''),
                'Quantity': r.get('quantity', 0),
                'Average Cost': round(float(r.get('avg_cost', 0)), 2),
                'LTP': round(float(r.get('ltp', 0)), 2),
                'Day Change': round(float(r.get('day_change', 0)), 2),
                'Day Change %': round(float(r.get('day_change_pct', 0)), 2),
                'Invested Amount': round(float(r.get('invested_amount', 0)), 2),
                'Current Value': round(float(r.get('current_value', 0)), 2),
                'Unrealized P&L': round(float(r.get('unrealized_pnl', 0)), 2),
                'P&L %': round(float(r.get('pnl_percent', 0)), 2),
                'Action': r.get('action', ''),
                'Reason': r.get('reason', ''),
                'Realized Profit': round(float(r.get('realized_profit', 0)), 2),
            })

        df = pd.DataFrame(rows)

        # Write to Excel in memory
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Portfolio')
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="portfolio_export.xlsx"'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Export failed: {type(e).__name__}: {e}")
        return redirect('dashboard')


def upload_pnl(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = handle_uploaded_file(request.FILES['file'])
            if df is not None:
                # Strict Header Validation
                uploaded_headers = list(df.columns)
                if uploaded_headers != PNL_HEADERS:
                    messages.error(request, "No matched with Sample Header of data.")
                    return redirect('upload_pnl')

                count = 0
                for _, row in df.iterrows():
                    symbol = row.get('Symbol')
                    qty = clean_numeric(row.get('Quantity'), to_int=True)
                    sell_val = clean_numeric(row.get('Sell Value'))
                    buy_val = clean_numeric(row.get('Buy Value'))
                    profit = clean_numeric(row.get('Profit'))
                    entry_date = row.get('Entry Date')
                    exit_date = row.get('Exit Date')
                    
                    # Basic validation
                    if symbol and qty and profit:
                        # Get Instrument (must be verified)
                        from core.utils import resolve_instrument
                        inst = resolve_instrument(symbol.strip())
                        if not inst:
                            messages.warning(request, f"Skipped '{symbol}': Not in verified database.")
                            continue
                        
                        # Duplicate prevention: Symbol + Quantity + Sell Value
                        exists = PnLStatement.objects.filter(
                            user=request.user,
                            instrument=inst,
                            quantity=qty,
                            sell_value=sell_val
                        ).exists()
                        
                        if not exists:
                            PnLStatement.objects.create(
                                user=request.user,
                                instrument=inst,
                                quantity=qty,
                                buy_value=buy_val or 0,
                                sell_value=sell_val or 0,
                                realized_profit=profit,
                                entry_date=pd.to_datetime(entry_date).date() if entry_date and str(entry_date).lower() != 'nan' else None,
                                exit_date=pd.to_datetime(exit_date).date() if exit_date and str(exit_date).lower() != 'nan' else None
                            )
                            count += 1
                messages.success(request, f"{count} P&L records uploaded.")
                return redirect('dashboard')
    else:
        form = UploadFileForm()
    return render(request, 'core/upload.html', {'form': form, 'title': 'Upload P&L Statement'})

@csrf_exempt
def send_signup_otp(request):
    """AJAX endpoint: sends a 6-digit OTP to the given email (pre-signup)."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
        email = body.get('email', '').strip().lower()
    except Exception:
        email = request.POST.get('email', '').strip().lower()

    if not email:
        return JsonResponse({'status': 'error', 'message': 'Email is required.'}, status=400)

    # Validate it looks like an email
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'status': 'error', 'message': 'Enter a valid email address.'}, status=400)

    # Block already-registered emails
    if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
        return JsonResponse({'status': 'error', 'message': 'This email is already registered. Please login instead.'}, status=400)

    # Generate OTP
    code = str(random.randint(100000, 999999))
    SignupOTP.objects.filter(email__iexact=email).delete()
    SignupOTP.objects.create(email=email, code=code)

    # Send email
    try:
        send_mail(
            subject='Your NPITS Registration Code',
            message=(
                f'Your 6-digit verification code is: {code}\n\n'
                f'This code is valid for 10 minutes.\n\n'
                f'If you did not request this, please ignore this email.'
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Failed to send email: {type(e).__name__}. Please try again.'}, status=500)

    return JsonResponse({'status': 'ok', 'message': f'OTP sent to {email}'})


@csrf_exempt
def verify_signup_otp(request):
    """AJAX endpoint: verifies OTP entered during signup. Sets session flag on success."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    import json as _json
    try:
        body = _json.loads(request.body)
        email = body.get('email', '').strip().lower()
        code = body.get('otp', '').strip()
    except Exception:
        email = request.POST.get('email', '').strip().lower()
        code = request.POST.get('otp', '').strip()

    if not email or not code:
        return JsonResponse({'status': 'error', 'message': 'Email and OTP are required.'}, status=400)

    otp_obj = SignupOTP.objects.filter(email__iexact=email, code=code).first()
    if not otp_obj:
        return JsonResponse({'status': 'error', 'message': 'Invalid OTP. Please check and try again.'}, status=400)
    if not otp_obj.is_valid():
        otp_obj.delete()
        return JsonResponse({'status': 'error', 'message': 'OTP has expired. Please request a new one.'}, status=400)

    # Mark in session
    request.session['signup_otp_verified'] = True
    request.session['signup_verified_email'] = email
    return JsonResponse({'status': 'ok', 'message': 'Email verified successfully!'})


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            post_email = form.cleaned_data.get('email', '').strip().lower()

            # Gate: OTP must be verified in session
            otp_verified = request.session.get('signup_otp_verified')
            verified_email = request.session.get('signup_verified_email', '').strip().lower()

            if not otp_verified or verified_email != post_email:
                messages.error(request, 'Please verify your email with the OTP before signing up.')
                return render(request, 'registration/register.html', {'form': form})

            user = form.save()

            # Clean up session flags and OTP record
            request.session.pop('signup_otp_verified', None)
            request.session.pop('signup_verified_email', None)
            SignupOTP.objects.filter(email__iexact=post_email).delete()

            login(request, user, backend='core.backends.EmailOrMobileBackend')

            # Send Welcome Email
            try:
                send_mail(
                    subject='Welcome to NPITS',
                    message=f'Hi {user.email},\n\nWelcome to Net Profit Investment Tracking System. Thank you for registering with us.\n\nBest Regards,\nNPITS Team',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, "Registration successful. Welcome email sent.")
            except Exception as e:
                print(f"Error sending email: {e}")
                messages.success(request, "Registration successful, but failed to send welcome email.")

            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def edit_portfolio_item(request, pk):
    item = get_object_or_404(Portfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PortfolioForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {item.instrument.symbol} successfully.")
            return redirect('dashboard')
    else:
        form = PortfolioForm(instance=item)
    return render(request, 'core/edit_portfolio.html', {'form': form, 'item': item})

@login_required
def delete_portfolio_item(request, pk):
    item = get_object_or_404(Portfolio, pk=pk, user=request.user)
    symbol = item.instrument.symbol
    if request.method == 'POST':
        item.delete()
        messages.success(request, f"Deleted {symbol} from portfolio.")
        return redirect('dashboard')
    return render(request, 'core/delete_confirm.html', {'item': item})

@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('dashboard')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'core/edit_profile.html', {'form': form})


@login_required
@csrf_exempt
def buy_stock(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').strip().upper()
        quantity_str = request.POST.get('quantity', '0')
        price_str = request.POST.get('price', '0')
        
        try:
            quantity = int(quantity_str)
            price = Decimal(price_str)
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity or price.")
            return redirect('dashboard')
        date_str = request.POST.get('date')
        
        transaction_date = pd.to_datetime(date_str).date() if date_str else timezone.now().date()
        
        try:
            inst = Instrument.objects.get(symbol__iexact=symbol, is_verified=True)
        except Instrument.DoesNotExist:
            # Fallback for manual addition if not found or not verified
            inst, _ = Instrument.objects.get_or_create(symbol=symbol, defaults={'name': symbol, 'is_verified': True})
        
        # Create Transaction record
        Transaction.objects.create(
            user=request.user,
            instrument=inst,
            transaction_type='BUY',
            quantity=quantity,
            remaining_quantity=quantity,
            price=price,
            date=transaction_date
        )
        
        portfolio, created = Portfolio.objects.get_or_create(
            user=request.user, 
            instrument=inst,
            defaults={'quantity': 0, 'avg_cost': Decimal('0'), 'ltp': price}
        )
        
        # Update Weighted Average Cost for Portfolio summary
        current_total_cost = Decimal(str(portfolio.quantity)) * portfolio.avg_cost
        new_total_cost = Decimal(str(quantity)) * price
        total_quantity = portfolio.quantity + quantity
        
        new_avg_cost = (current_total_cost + new_total_cost) / Decimal(str(total_quantity))
        
        portfolio.quantity = total_quantity
        portfolio.avg_cost = new_avg_cost
        # Only update LTP if it was 0 or just created
        if created or not portfolio.ltp or portfolio.ltp == 0:
            portfolio.ltp = price
        portfolio.save()
        
        messages.success(request, f"Bought {quantity} units of {symbol} at {price}")
        return redirect('dashboard')
    return redirect('dashboard')

@login_required
@csrf_exempt
def sell_stock(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol').strip().upper()
        quantity_to_sell = int(request.POST.get('quantity'))
        price = Decimal(request.POST.get('price'))
        exit_date_str = request.POST.get('exit_date')
        exit_date = pd.to_datetime(exit_date_str).date() if exit_date_str else timezone.now().date()
        
        inst = get_object_or_404(Instrument, symbol__iexact=symbol, is_verified=True)
        portfolio = get_object_or_404(Portfolio, user=request.user, instrument=inst)
        
        if quantity_to_sell > portfolio.quantity:
            messages.error(request, f"Insufficient quantity to sell. You have {portfolio.quantity} units.")
            return redirect('dashboard')
            
        # 1. Intraday Logic: Check for a matching BUY today with same volume
        intraday_buy = Transaction.objects.filter(
            user=request.user,
            instrument=inst,
            transaction_type='BUY',
            date=exit_date,
            quantity=quantity_to_sell,
            remaining_quantity=quantity_to_sell
        ).first()

        total_buy_value = Decimal('0')
        remaining_to_deduct = quantity_to_sell
        first_entry_date = None

        if intraday_buy:
            total_buy_value = Decimal(str(quantity_to_sell)) * intraday_buy.price
            first_entry_date = intraday_buy.date
            intraday_buy.remaining_quantity = 0
            intraday_buy.save()
            remaining_to_deduct = 0
        else:
            # 2. FIFO Logic: Fetch active buy transactions
            buy_txs = Transaction.objects.filter(
                user=request.user,
                instrument=inst,
                transaction_type='BUY',
                remaining_quantity__gt=0
            ).order_by('date', 'created_at')
            
            for tx in buy_txs:
                if remaining_to_deduct <= 0:
                    break
                
                if first_entry_date is None:
                    first_entry_date = tx.date
                    
                deduct = min(tx.remaining_quantity, remaining_to_deduct)
                total_buy_value += Decimal(str(deduct)) * tx.price
                tx.remaining_quantity -= deduct
                tx.save()
                remaining_to_deduct -= deduct
            
        sell_value = Decimal(str(quantity_to_sell)) * price
        profit = sell_value - total_buy_value
        
        # Record Sell Transaction
        Transaction.objects.create(
            user=request.user,
            instrument=inst,
            transaction_type='SELL',
            quantity=quantity_to_sell,
            price=price,
            date=exit_date
        )
        
        # Record in PnLStatement
        PnLStatement.objects.create(
            user=request.user,
            instrument=inst,
            entry_date=first_entry_date,
            quantity=quantity_to_sell,
            buy_value=total_buy_value,
            sell_value=sell_value,
            realized_profit=profit,
            exit_date=exit_date
        )
        
        # Update Portfolio
        portfolio.quantity -= quantity_to_sell
        if portfolio.quantity <= 0:
            portfolio.delete()
        else:
            # Recalculate average cost based on remaining lots
            remaining_lots = Transaction.objects.filter(
                user=request.user,
                instrument=inst,
                transaction_type='BUY',
                remaining_quantity__gt=0
            )
            if remaining_lots.exists():
                total_qty = sum(l.remaining_quantity for l in remaining_lots)
                total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in remaining_lots)
                portfolio.avg_cost = total_cost / Decimal(str(total_qty))
            
            # Save the updated quantity and (potentially) avg_cost
            portfolio.save()
            
        messages.success(request, f"Sold {quantity_to_sell} units of {symbol} at {price}. Profit: {profit}")
        return redirect('dashboard')
def get_current_financial_year():
    now = timezone.now().date()
    # Standard Indian Financial Year starts April 1.
    # User requested transition to 2026-2027 starting March 27, 2026.
    if now.month >= 4 or (now.year == 2026 and now.month == 3 and now.day >= 27):
        return f"{now.year}-{now.year+1}"
    else:
        return f"{now.year-1}-{now.year}"

@login_required
def transaction_history(request):
    """View all buy/sell transactions for the user."""
    transactions = Transaction.objects.filter(user=request.user).select_related('instrument').order_by('-date', '-created_at')
    
    current_fy_str = get_current_financial_year()
    portfolios = Portfolio.objects.filter(user=request.user)
    current_invested = sum(p.invested_amount for p in portfolios)
    current_value = sum(p.current_value for p in portfolios)
    current_unrealized = sum(p.unrealized_pnl for p in portfolios)
    
    start_year = int(current_fy_str.split('-')[0])
    end_year = int(current_fy_str.split('-')[1])
    from .models import FinancialYearData
    
    total_realized_profits = PnLStatement.objects.filter(user=request.user)
    total_realized = sum(rp.realized_profit for rp in total_realized_profits)
    
    past_fys = FinancialYearData.objects.filter(user=request.user).exclude(financial_year=current_fy_str)
    past_fys_realized_sum = sum(fd.realized_profit for fd in past_fys)
    
    current_realized = total_realized - past_fys_realized_sum
    
    # Automatically add/update current FY
    current_fy_obj, _ = FinancialYearData.objects.update_or_create(
        user=request.user,
        financial_year=current_fy_str,
        defaults={
            'invested_amount': current_invested,
            'current_value': current_value,
            'unrealized_pnl': current_unrealized,
            'realized_profit': current_realized
        }
    )
    
    # Get all FY data (including current that we just saved/updated) ordered by most recent
    fy_data = FinancialYearData.objects.filter(user=request.user).order_by('-financial_year')
    current_fy_data = [fd for fd in fy_data if fd.financial_year == current_fy_str]
    past_fy_data = [fd for fd in fy_data if fd.financial_year != current_fy_str]
    
    return render(request, 'core/transactions.html', {
        'transactions': transactions,
        'current_fy_data': current_fy_data[0] if current_fy_data else None,
        'past_fy_data': past_fy_data
    })

@login_required
@csrf_exempt
def save_fy_data(request):
    if request.method == 'POST':
        import json
        from decimal import Decimal
        try:
            data = json.loads(request.body)
            from .models import FinancialYearData
            for row in data:
                fy = row.get('year')
                if fy:
                    obj = FinancialYearData.objects.filter(user=request.user, financial_year=fy).first()
                    invested = Decimal(str(row.get('invested', 0)))
                    current = Decimal(str(row.get('current', 0)))
                    unrealized = Decimal(str(row.get('unrealized', 0)))
                    realized = Decimal(str(row.get('realized', 0)))
                    
                    if obj:
                        if obj.is_locked: 
                            continue # Locked, silently ignore
                        
                        # Only update if data actually changed
                        if (obj.invested_amount != invested or 
                            obj.current_value != current or 
                            obj.unrealized_pnl != unrealized or 
                            obj.realized_profit != realized):
                            
                            obj.invested_amount = invested
                            obj.current_value = current
                            obj.unrealized_pnl = unrealized
                            obj.realized_profit = realized
                            obj.save()
                    else:
                        FinancialYearData.objects.create(
                            user=request.user,
                            financial_year=fy,
                            invested_amount=invested,
                            current_value=current,
                            unrealized_pnl=unrealized,
                            realized_profit=realized,
                            edit_count=1
                        )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@login_required
@csrf_exempt
def toggle_fy_lock(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            fy = data.get('year')
            from .models import FinancialYearData
            obj = get_object_or_404(FinancialYearData, user=request.user, financial_year=fy)
            obj.is_locked = not obj.is_locked
            obj.save()
            return JsonResponse({'status': 'success', 'is_locked': obj.is_locked})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@login_required
@csrf_exempt
def delete_fy_data(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            fy = data.get('year')
            from .models import FinancialYearData
            obj = get_object_or_404(FinancialYearData, user=request.user, financial_year=fy)
            if obj.is_locked:
                return JsonResponse({'status': 'error', 'message': 'Cannot delete a locked record.'}, status=403)
            obj.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@login_required
def lot_breakdown(request, instrument_id):
    """View specific buy lots for a particular instrument."""
    inst = get_object_or_404(Instrument, id=instrument_id)
    lots = Transaction.objects.filter(
        user=request.user,
        instrument=inst,
        transaction_type='BUY',
        remaining_quantity__gt=0
    ).order_by('date', 'created_at')
    
    # Enrich lots with days held and unrealized P&L
    live_ltps = fetch_live_ltp()
    ltp = Decimal(str(live_ltps.get(inst.symbol.upper(), 0))) or Decimal('0')
    
    enriched_lots = []
    for lot in lots:
        days_held = (timezone.now().date() - lot.date).days
        current_value = Decimal(str(lot.remaining_quantity)) * ltp
        buy_value = Decimal(str(lot.remaining_quantity)) * lot.price
        pnl = current_value - buy_value
        pnl_pct = (pnl / buy_value * 100) if buy_value else 0
        
        enriched_lots.append({
            'id': lot.id,
            'date': lot.date,
            'quantity': lot.remaining_quantity,
            'price': lot.price,
            'days_held': days_held,
            'ltp': ltp,
            'unrealized_pnl': pnl,
            'pnl_pct': pnl_pct
        })
        
    total_quantity = sum(l['quantity'] for l in enriched_lots)
    total_invested = sum(Decimal(str(l['quantity'])) * l['price'] for l in enriched_lots)
    avg_cost = total_invested / Decimal(str(total_quantity)) if total_quantity > 0 else 0
    
    context = {
        'instrument': inst,
        'lots': enriched_lots,
        'total_quantity': total_quantity,
        'total_invested': total_invested,
        'avg_cost': avg_cost,
    }
    return render(request, 'core/lot_breakdown.html', context)

@login_required
def edit_lot(request, pk):
    """Edit an individual purchase lot."""
    lot = get_object_or_404(Transaction, pk=pk, user=request.user, transaction_type='BUY')
    
    if request.method == 'POST':
        try:
            new_qty = int(request.POST.get('quantity'))
            new_price = Decimal(request.POST.get('price'))
            new_date = pd.to_datetime(request.POST.get('date')).date()
            
            # Difference in quantity
            qty_diff = new_qty - lot.remaining_quantity
            
            lot.quantity = new_qty
            lot.remaining_quantity = new_qty
            lot.price = new_price
            lot.date = new_date
            lot.save()
            
            # Update Portfolio
            portfolio = Portfolio.objects.get(user=request.user, instrument=lot.instrument)
            portfolio.quantity += qty_diff
            
            # Recalculate average cost
            all_lots = Transaction.objects.filter(
                user=request.user, 
                instrument=lot.instrument, 
                transaction_type='BUY', 
                remaining_quantity__gt=0
            )
            total_qty = sum(l.remaining_quantity for l in all_lots)
            total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in all_lots)
            portfolio.avg_cost = total_cost / Decimal(str(total_qty)) if total_qty > 0 else 0
            
            if portfolio.quantity <= 0:
                portfolio.delete()
            else:
                portfolio.save()
                
            messages.success(request, f"Lot for {lot.instrument.symbol} updated successfully.")
            return redirect('lot_breakdown', instrument_id=lot.instrument.id)
        except Exception as e:
            messages.error(request, f"Error updating lot: {e}")
            
    return render(request, 'core/edit_lot.html', {'lot': lot, 'form': EditLotForm(initial={
        'quantity': lot.remaining_quantity,
        'price': lot.price,
        'date': lot.date
    })})

@login_required
def delete_lot(request, pk):
    """Delete an individual purchase lot."""
    lot = get_object_or_404(Transaction, pk=pk, user=request.user, transaction_type='BUY')
    instrument = lot.instrument
    instrument_id = instrument.id
    
    # Update Portfolio before deleting
    try:
        portfolio = Portfolio.objects.get(user=request.user, instrument=instrument)
        portfolio.quantity -= lot.remaining_quantity
        
        lot.delete()
        
        # Recalculate average cost
        remaining_lots = Transaction.objects.filter(
            user=request.user, 
            instrument=instrument, 
            transaction_type='BUY', 
            remaining_quantity__gt=0
        )
        
        if not remaining_lots.exists():
            portfolio.delete()
        else:
            total_qty = sum(l.remaining_quantity for l in remaining_lots)
            total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in remaining_lots)
            portfolio.avg_cost = total_cost / Decimal(str(total_qty))
            portfolio.save()
            
        messages.success(request, f"Lot deleted successfully.")
    except Portfolio.DoesNotExist:
        lot.delete()
        messages.success(request, f"Lot deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting lot: {e}")
        
    return redirect('lot_breakdown', instrument_id=instrument_id)
@csrf_exempt
def sync_data_api(request):
    """API endpoint to trigger data synchronization with rate limiting via cache."""
    sync_key = 'last_sync_timestamp'
    lock_key = 'sync_in_progress'
    
    # Rate limit: 1 minute
    last_sync = cache.get(sync_key)
    now = timezone.now().timestamp()
    
    if last_sync is not None and (now - last_sync) < 60:
        return JsonResponse({'status': 'skipped', 'message': 'Recently synced'})
    
    if cache.get(lock_key):
        return JsonResponse({'status': 'skipped', 'message': 'Sync in progress'})
    
    # Set lock and timestamp
    cache.set(lock_key, True, 300) # 5 min safety lock
    cache.set(sync_key, now, 3600)
    
    try:
        perform_sync()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    finally:
        cache.delete(lock_key)

def assetlinks_json(request):
    """
    Serve the Digital Asset Links file for Android TWA verification.
    """
    asset_links = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "in.npits.twa",
                "sha256_cert_fingerprints": [
                    "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00"
                ]
            }
        }
    ]
    return JsonResponse(asset_links, safe=False)

@csrf_exempt
def index_data_api(request):
    """Fetch historical OHLC data for indices, commodities, and global markets."""
    symbol = request.GET.get('symbol', '^NSEI')
    name = request.GET.get('name', '')
    period = request.GET.get('period', '1d')
    
    # Mapping for common intervals
    interval_map = {
        '1d': '5m',
        '1mo': '1d',
        '6mo': '1d',
        '9mo': '1d',
        '1y': '1d',
        'max': '1wk'
    }
    interval = interval_map.get(period, '1d')

    try:
        cache_key = f'index_data_{symbol}_{period}'
        data = cache.get(cache_key)
        if data:
            return JsonResponse(data)

        ticker = yf.Ticker(symbol)
        # For 1d, sometimes data is delayed or empty on weekends. Try 5d if 1d fails.
        hist = ticker.history(period=period, interval=interval)
        
        # Drop rows with NaN Close values (e.g. incomplete current week for futures)
        hist = hist.dropna(subset=['Close'])
        
        if hist.empty and period == '1d':
            hist = ticker.history(period='5d', interval='5m')
            hist = hist.dropna(subset=['Close'])
            
        if hist.empty:
            return JsonResponse({'status': 'error', 'message': f'No data found for {symbol}'}, status=404)

        # Prepare data for Chart.js
        if period == '1d':
            # For 1d, only show today's data or the last available day's data
            last_date = hist.index[-1].date()
            day_data = hist[hist.index.date == last_date]
            if day_data.empty: day_data = hist.tail(50) # Fallback
            labels = [d.strftime('%H:%M') for d in day_data.index]
            prices = [round(float(p), 2) for p in day_data['Close']]
        elif period == 'max':
            labels = [d.strftime('%Y') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
        else:
            labels = [d.strftime('%Y-%m-%d') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
            
        # Calculate change info based on the fetched history
        current_price = prices[-1]

        if period == '1d':
            # Proper 1-day change: relative to previous day's close
            # Avoid using ticker.info as it is unreliable and slow. Use history instead.
            try:
                hist_daily = ticker.history(period='5d', interval='1d')
                if len(hist_daily) >= 2:
                    prev_price = float(hist_daily['Close'].iloc[-2])
                else:
                    prev_price = float(hist_daily['Close'].iloc[-1]) if not hist_daily.empty else prices[0]
            except:
                prev_price = prices[0] # Fallback to open
        else:
            prev_price = prices[0]

        change = round(current_price - prev_price, 2)
        change_pct = round((change / prev_price) * 100, 2) if prev_price else 0

        # Heuristic for display name if not provided
        if not name:
            if '^NSEI' in symbol: name = 'NIFTY 50'
            elif '^BSESN' in symbol: name = 'SENSEX'
            elif '^IXIC' in symbol: name = 'NASDAQ'
            elif '^DJI' in symbol: name = 'DOW JONES'
            else: name = symbol

        result = {
            'labels': labels,
            'prices': prices,
            'current_price': current_price,
            'previous_close': prev_price,
            'change': change,
            'change_pct': change_pct,
            'symbol_name': name,
            'symbol': symbol,
            'period': period
        }
        
        cache.set(cache_key, result, 300) # 5 mins
        return JsonResponse(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def stock_price_api(request):
    """Fetch live price and basic info for any stock symbol."""
    symbol = request.GET.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)

    # Smart symbol handling: don't append .NS to indices, commodities, or already suffixed symbols
    if any(x in symbol for x in ['^', '.', '=F']):
        symbol_ns = symbol
    else:
        symbol_ns = f"{symbol}.NS"

    try:
        cache_key = f'stock_price_{symbol_ns}'
        data = cache.get(cache_key)
        if data:
            return JsonResponse(data)

        ticker = yf.Ticker(symbol_ns)
        hist = ticker.history(period='5d') # Get 5 days to be safe with weekends
        
        if hist.empty:
            if symbol_ns.endswith('.NS'):
                symbol_ns = f"{symbol}.BO"
                ticker = yf.Ticker(symbol_ns)
                hist = ticker.history(period='5d')
                if hist.empty:
                    return JsonResponse({'status': 'error', 'message': 'Stock not found'}, status=404)
            else:
                return JsonResponse({'status': 'error', 'message': 'Stock not found'}, status=404)

        info = ticker.info
        current_price = round(float(hist['Close'].iloc[-1]), 2)
        
        # Prioritize info previousClose for accuracy
        prev_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
        if not prev_close:
            prev_close = round(float(hist['Close'].iloc[-2]), 2) if len(hist) > 1 else current_price
        
        change = round(current_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        result = {
            'symbol': symbol_ns,
            'name': info.get('longName', symbol),
            'price': current_price,
            'previous_close': prev_close,
            'change': change,
            'change_pct': change_pct,
            'currency': info.get('currency', 'INR'),
            'market': info.get('market', 'in_market'),
            'pe': info.get('trailingPE'),
            'volume': info.get('volume'),
            'avg_volume': info.get('averageVolume'),
            'eps': info.get('trailingEps'),
            'high52': info.get('fiftyTwoWeekHigh'),
            'low52': info.get('fiftyTwoWeekLow'),
            'market_cap': info.get('marketCap'),
            'dividend': info.get('dividendYield')
        }
        
        cache.set(cache_key, result, 60) # 1 min cache for live prices
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def stock_suggestions_api(request):
    """Provide real-time suggestions based on symbol or name from our DB."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'status': 'success', 'results': []})

    from core.models import Instrument
    results = Instrument.objects.filter(
        models.Q(symbol__icontains=q) | models.Q(name__icontains=q),
        is_verified=True
    ).values('symbol', 'name')[:10]

    return JsonResponse({'status': 'success', 'results': list(results)})

@csrf_exempt
def stock_history_api(request):
    """Fetch historical OHLC data for any stock symbol."""
    symbol = request.GET.get('symbol', '').strip().upper()
    period = request.GET.get('period', '1d')
    
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)

    # Smart symbol handling: append .NS if no suffix
    if not any(x in symbol for x in ['^', '.', '=F']):
        symbol_ns = f"{symbol}.NS"
    else:
        symbol_ns = symbol

    # Mapping for common intervals
    interval_map = {
        '1d': '5m',
        '1mo': '1d',
        '6mo': '1d',
        '9mo': '1d',
        '1y': '1d',
        'max': '1wk'
    }
    interval = interval_map.get(period, '1d')

    try:
        cache_key = f'stock_history_{symbol_ns}_{period}'
        data = cache.get(cache_key)
        if data:
            return JsonResponse(data)

        ticker = yf.Ticker(symbol_ns)
        hist = ticker.history(period=period, interval=interval)
        
        hist = hist.dropna(subset=['Close'])
        
        if hist.empty and period == '1d':
            hist = ticker.history(period='5d', interval='5m')
            hist = hist.dropna(subset=['Close'])
            
        if hist.empty:
            if symbol_ns.endswith('.NS'):
                symbol_ns = symbol_ns.replace('.NS', '.BO')
                ticker = yf.Ticker(symbol_ns)
                hist = ticker.history(period=period, interval=interval)
                hist = hist.dropna(subset=['Close'])
                if hist.empty and period == '1d':
                    hist = ticker.history(period='5d', interval='5m')
                    hist = hist.dropna(subset=['Close'])

        if hist.empty:
            return JsonResponse({'status': 'error', 'message': f'No history found for {symbol_ns}'}, status=404)

        # Prepare data for Chart.js
        if period == '1d':
            last_date = hist.index[-1].date()
            day_data = hist[hist.index.date == last_date]
            if day_data.empty: day_data = hist.tail(50)
            labels = [d.strftime('%H:%M') for d in day_data.index]
            prices = [round(float(p), 2) for p in day_data['Close']]
        elif period == 'max':
            labels = [d.strftime('%Y') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
        else:
            labels = [d.strftime('%Y-%m-%d') for d in hist.index]
            prices = [round(float(p), 2) for p in hist['Close']]
            
        current_price = prices[-1]

        if period == '1d':
            # Avoid using ticker.info as it is unreliable and slow. Use history instead.
            try:
                hist_daily = ticker.history(period='5d', interval='1d')
                if len(hist_daily) >= 2:
                    prev_price = float(hist_daily['Close'].iloc[-2])
                else:
                    prev_price = float(hist_daily['Close'].iloc[-1]) if not hist_daily.empty else prices[0]
            except:
                prev_price = prices[0]
        else:
            prev_price = prices[0]

        change = round(current_price - prev_price, 2)
        change_pct = round((change / prev_price) * 100, 2) if prev_price else 0

        result = {
            'labels': labels,
            'prices': prices,
            'current_price': current_price,
            'previous_close': prev_price,
            'change': change,
            'change_pct': change_pct,
            'symbol': symbol_ns,
            'period': period
        }
        
        cache.set(cache_key, result, 300)
        return JsonResponse(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def watchlist(request):
    """View to display the user's personal watchlist."""
    from core.models import Watchlist, Portfolio
    from .utils import fetch_live_ltp
    
    watchlist_items = Watchlist.objects.filter(user=request.user).select_related('instrument')
    # Get portfolio data to support actions
    portfolio_data = {p.instrument_id: {'qty': p.quantity, 'invested': float(p.invested_amount or 0)} 
                      for p in Portfolio.objects.filter(user=request.user)}
    
    live_ltps = fetch_live_ltp() or {}
    results = []
    for item in watchlist_items:
        inst = item.instrument
        if not inst:
            continue
            
        ltp = float(live_ltps.get(inst.symbol.upper(), 0))
        if ltp <= 0:
            ltp = float(inst.last_price or 0)
            
        change = float(inst.price_change or 0)
        prev_close = ltp - change
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        p_data = portfolio_data.get(inst.id, {'qty': 0, 'invested': 0})
        
        h52 = float(inst.high_52w or 0)
        diff_52w_pct = (ltp / h52 - 1) * 100 if h52 > 0 else 0
        
        results.append({
            'symbol': inst.symbol,
            'name': inst.name,
            'ltp': ltp,
            'change': change,
            'change_pct': change_pct,
            'high_52w': h52,
            'diff_52w_pct': diff_52w_pct,
            'notes': item.notes,
            'added_at': item.added_at,
            'instrument_id': inst.id,
            'portfolio_qty': p_data['qty'],
            'invested_amount': p_data['invested']
        })
        
    return render(request, 'core/watchlist.html', {'watchlist': results})

@csrf_exempt
@login_required
def add_to_watchlist_api(request):
    """API to add a symbol to the user's watchlist."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    symbol = request.POST.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)
    
    from .models import Instrument, Watchlist
    import yfinance as yf
    
    # Try to find the instrument
    instrument = Instrument.objects.filter(symbol__iexact=symbol).first()
    
    if not instrument:
        # Try to find exactly as provided or with .NS
        search_symbol = symbol if '.' in symbol else f"{symbol}.NS"
        try:
            ticker = yf.Ticker(search_symbol)
            info = ticker.info
            if info and 'symbol' in info and info.get('symbol'):
                fetched_symbol = str(info.get('symbol')).upper()
                instrument, _ = Instrument.objects.get_or_create(
                    symbol=fetched_symbol,
                    defaults={
                        'name': info.get('longName') or info.get('shortName') or symbol,
                        'last_price': info.get('regularMarketPrice') or info.get('previousClose') or 0,
                        'is_verified': True
                    }
                )
            else:
                return JsonResponse({'status': 'error', 'message': f'Symbol {symbol} not found in market'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc() # Log to server console
            return JsonResponse({'status': 'error', 'message': f'Error fetching symbol: {str(e)}'}, status=500)

    try:
        Watchlist.objects.get_or_create(user=request.user, instrument=instrument)
        return JsonResponse({'status': 'success', 'message': f'{symbol} added to watchlist'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Error saving to watchlist: {str(e)}'}, status=500)

@csrf_exempt
@login_required
def remove_from_watchlist_api(request):
    """API to remove a symbol from the user's watchlist."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    symbol = request.POST.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol is required'}, status=400)
    
    from core.models import Instrument, Watchlist
    instrument = Instrument.objects.filter(symbol__iexact=symbol).first()
    
    if instrument:
        Watchlist.objects.filter(user=request.user, instrument=instrument).delete()
        return JsonResponse({'status': 'success', 'message': f'{symbol} removed from watchlist'})
    
    return JsonResponse({'status': 'error', 'message': 'Instrument not found'}, status=404)

@login_required
def auto_migrate(request):
    """Temporary utility to run migrations from the browser."""
    from django.http import HttpResponse # Import inside for safety
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized. Superuser access required.", status=403)
    
    from django.core.management import call_command
    import io
    from django.utils import timezone
    
    output = io.StringIO()
    try:
        output.write(f"--- Migration Started at {timezone.now()} ---\n")
        
        # 1. Run makemigrations
        output.write("Running makemigrations core...\n")
        call_command('makemigrations', 'core', stdout=output)
        
        # 2. Run migrate
        output.write("\nRunning migrate core...\n")
        call_command('migrate', 'core', stdout=output)
        
        output.write(f"\n--- Migration Finished Successfully ---\n")
        return HttpResponse(f"<h1>Migration Success</h1><pre>{output.getvalue()}</pre>")
    except Exception as e:
        output.write(f"\nCRITICAL ERROR: {str(e)}\n")
        return HttpResponse(f"<h1>Migration Failed</h1><pre>{output.getvalue()}</pre>", status=500)

@login_required
def mf_suggestions_api(request):
    """API for Mutual Fund autocomplete by name or symbol."""
    from django.db.models import Q
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)
    
    # Search specifically in MutualFund model (populated from Excel)
    funds = MutualFund.objects.filter(
        Q(name__icontains=query) | Q(symbol__icontains=query)
    )[:15]
    
    results = [
        {
            'name': f.name,
            'symbol': f.symbol,
            'nav': float(f.nav) if f.nav else 0
        } for f in funds
    ]
    return JsonResponse(results, safe=False)

@csrf_exempt
def coin_price_api(request):
    """API to fetch live price for a coin symbol via yfinance."""
    symbol = request.GET.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol required'}, status=400)
    
    # Handle crypto symbols (BTC -> BTC-INR)
    if '-' not in symbol and not symbol.endswith('.NS') and not symbol.endswith('.BO'):
        symbol = f"{symbol}-INR"
        
    try:
        ticker = yf.Ticker(symbol)
        # Fetch price reliably via history
        hist = ticker.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            try:
                # Provide a graceful fallback for name if info fails due to YF limits
                info = ticker.info
                name = info.get('shortName') or info.get('longName') or symbol
            except Exception:
                name = symbol
            
            return JsonResponse({
                'status': 'success',
                'symbol': symbol,
                'name': name,
                'price': float(price)
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Price not found in history'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def nps_dashboard(request):
    """NPS Portfolio Dashboard."""
    nps_holdings = NPSPortfolio.objects.filter(user=request.user).select_related('fund')
    nps_holdings = [h for h in nps_holdings if h.units > 0]
    total_invested = sum(h.invested_amount for h in nps_holdings)
    total_current_value = sum(h.current_value for h in nps_holdings)
    total_unrealized_pnl = sum(h.unrealized_pnl for h in nps_holdings)
    total_day_change = sum(h.day_change for h in nps_holdings)
    total_realized_profit = NPSPortfolio.objects.filter(user=request.user).aggregate(
        total=models.Sum('realized_profit'))['total'] or 0
    context = {
        'nps_holdings': nps_holdings,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_day_change': total_day_change,
        'total_realized_profit': total_realized_profit,
    }
    return render(request, 'core/nps_dashboard.html', context)

@login_required
def add_nps(request):
    if request.method == 'POST':
        fund_name = request.POST.get('fund_name').strip()
        units = Decimal(request.POST.get('units', '0'))
        avg_nav = Decimal(request.POST.get('avg_nav', '0'))
        date_str = request.POST.get('date')
        transaction_date = pd.to_datetime(date_str).date() if date_str else timezone.now().date()
        fund, _ = NPSFund.objects.get_or_create(name=fund_name)
        NPSTransaction.objects.create(
            user=request.user, fund=fund, transaction_type='BUY',
            units=units, remaining_units=units, price=avg_nav, date=transaction_date
        )
        holding, created = NPSPortfolio.objects.get_or_create(
            user=request.user, fund=fund, defaults={'units': 0, 'avg_nav': 0}
        )
        total_units = holding.units + units
        total_cost = (holding.units * holding.avg_nav) + (units * avg_nav)
        holding.units = total_units
        holding.avg_nav = total_cost / total_units if total_units > 0 else 0
        holding.save()
        messages.success(request, f"Added {units} units of {fund_name} to NPS.")
        return redirect('nps_dashboard')
    all_funds = NPSFund.objects.all().order_by('name')
    return render(request, 'core/nps_add_item.html', {'all_funds': all_funds})

@login_required
def sell_nps(request, pk):
    holding = get_object_or_404(NPSPortfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        units_to_sell = Decimal(request.POST.get('units', '0'))
        sell_price = Decimal(request.POST.get('price', '0'))
        date_str = request.POST.get('date')
        sell_date = pd.to_datetime(date_str).date() if date_str else timezone.now().date()
        if units_to_sell > holding.units:
            messages.error(request, f"Insufficient units.")
            return redirect('nps_dashboard')
        buy_lots = NPSTransaction.objects.filter(
            user=request.user, fund=holding.fund, transaction_type='BUY', remaining_units__gt=0
        ).order_by('date', 'created_at')
        total_buy_cost = Decimal('0')
        remaining_to_sell = units_to_sell
        for lot in buy_lots:
            if remaining_to_sell <= 0: break
            deduct = min(lot.remaining_units, remaining_to_sell)
            total_buy_cost += deduct * lot.price
            lot.remaining_units -= deduct
            lot.save()
            remaining_to_sell -= deduct
        realized_profit = (units_to_sell * sell_price) - total_buy_cost
        NPSTransaction.objects.create(
            user=request.user, fund=holding.fund, transaction_type='SELL',
            units=units_to_sell, price=sell_price, date=sell_date
        )
        holding.units -= units_to_sell
        holding.realized_profit += realized_profit
        remaining_lots = NPSTransaction.objects.filter(
            user=request.user, fund=holding.fund, transaction_type='BUY', remaining_units__gt=0
        )
        total_rem_units = sum(l.remaining_units for l in remaining_lots)
        total_rem_cost = sum(l.remaining_units * l.price for l in remaining_lots)
        if total_rem_units > 0:
            holding.avg_nav = total_rem_cost / total_rem_units
        holding.save()
        messages.success(request, f"Sold {units_to_sell} units. Profit: ₹{realized_profit:.2f}")
        return redirect('nps_dashboard')
    return render(request, 'core/nps_sell_item.html', {'holding': holding, 'now': timezone.now()})

@login_required
def delete_nps_portfolio(request, pk):
    holding = get_object_or_404(NPSPortfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        name = holding.fund.name
        holding.delete()
        messages.success(request, f"Removed {name}.")
    return redirect('nps_dashboard')

@login_required
def nps_transaction_history(request):
    transactions = NPSTransaction.objects.filter(user=request.user).select_related('fund').order_by('-date', '-created_at')
    return render(request, 'core/nps_transactions.html', {'transactions': transactions})

@login_required
def refresh_nps_navs(request):
    from .utils import sync_nps_from_sheet
    count = sync_nps_from_sheet()
    if count > 0:
        messages.success(request, f"Synced {count} NPS Funds.")
    else:
        messages.warning(request, "NPS sync completed.")
    return redirect('nps_dashboard')

# --- FIXED ASSETS (FD) Module ---

@login_required
def fd_dashboard(request):
    """Dashboard for Fixed Assets (FD, PPF, etc)."""
    fd_holdings = FixedAsset.objects.filter(user=request.user).order_by('-investment_date')
    
    total_invested = sum(h.invested_amount for h in fd_holdings)
    total_current_value = sum(h.current_value for h in fd_holdings)
    total_unrealized_pnl = sum(h.unrealized_pnl for h in fd_holdings)
    
    total_pnl_pct = 0
    if total_invested > 0:
        total_pnl_pct = (total_unrealized_pnl / float(total_invested)) * 100
        
    context = {
        'fd_holdings': fd_holdings,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_pnl_pct': total_pnl_pct,
        'last_updated': timezone.now(),
    }
    return render(request, 'core/fd_dashboard.html', context)

@login_required
def add_fd(request):
    """Add a fixed asset manually."""
    if request.method == 'POST':
        instrument_name = request.POST.get('instrument_name', '').strip()
        investment_date_str = request.POST.get('investment_date')
        maturity_date_str = request.POST.get('maturity_date')
        
        try:
            invested_amount = Decimal(request.POST.get('invested_amount', '0'))
            interest_rate = Decimal(request.POST.get('interest_rate', '0'))
            investment_date = pd.to_datetime(investment_date_str).date() if investment_date_str else timezone.now().date()
            maturity_date = pd.to_datetime(maturity_date_str).date() if maturity_date_str else None
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric or date values provided.")
            return redirect('add_fd')

        if not instrument_name or invested_amount <= 0 or interest_rate <= 0:
            messages.error(request, "Please provide valid instrument name, amount, and rate.")
            return redirect('add_fd')
            
        FixedAsset.objects.create(
            user=request.user,
            instrument_name=instrument_name,
            invested_amount=invested_amount,
            interest_rate=interest_rate,
            investment_date=investment_date,
            maturity_date=maturity_date
        )
        messages.success(request, f"Added Fixed Asset: {instrument_name}.")
        return redirect('fd_dashboard')
        
    return render(request, 'core/fd_add_item.html')

@login_required
def delete_fd(request, pk):
    holding = get_object_or_404(FixedAsset, pk=pk, user=request.user)
    name = holding.instrument_name
    holding.delete()
    messages.success(request, f"Removed {name} from your Fixed Assets.")
    return redirect('fd_dashboard')

# --- OTHER ASSETS Module (Plots, Flats, Gold, etc) ---

@login_required
def other_assets_dashboard(request):
    """Dashboard for Other Assets (Plot, Flat, Gold, etc)."""
    other_holdings = OtherAsset.objects.filter(user=request.user).order_by('-purchase_date')
    
    total_invested = sum(h.purchase_price for h in other_holdings)
    total_current_value = sum(h.current_value for h in other_holdings)
    total_unrealized_pnl = sum(h.unrealized_pnl for h in other_holdings)
    total_monthly_rent = sum(h.monthly_rent for h in other_holdings)
    
    total_pnl_pct = 0
    if total_invested > 0:
        total_pnl_pct = (total_unrealized_pnl / float(total_invested)) * 100
        
    context = {
        'other_holdings': other_holdings,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_monthly_rent': total_monthly_rent,
        'total_pnl_pct': total_pnl_pct,
        'last_updated': timezone.now(),
    }
    return render(request, 'core/other_assets_dashboard.html', context)

@login_required
def add_other_asset(request):
    """Add a new other asset."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        asset_type = request.POST.get('asset_type', 'Other')
        purchase_date_str = request.POST.get('purchase_date')
        
        try:
            purchase_price = Decimal(request.POST.get('purchase_price', '0'))
            current_value = Decimal(request.POST.get('current_value', '0'))
            monthly_rent = Decimal(request.POST.get('monthly_rent', '0'))
            purchase_date = pd.to_datetime(purchase_date_str).date() if purchase_date_str else timezone.now().date()
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric or date values provided.")
            return redirect('add_other_asset')

        if not name or purchase_price < 0:
            messages.error(request, "Please provide valid name and purchase price.")
            return redirect('add_other_asset')
            
        OtherAsset.objects.create(
            user=request.user,
            name=name,
            asset_type=asset_type,
            purchase_date=purchase_date,
            purchase_price=purchase_price,
            current_value=current_value,
            monthly_rent=monthly_rent
        )
        messages.success(request, f"Added Asset: {name}.")
        return redirect('other_assets_dashboard')
        
    return render(request, 'core/other_asset_form.html', {'action': 'Add', 'asset_types': OtherAsset.ASSET_TYPES})

@login_required
def edit_other_asset(request, pk):
    """Edit an existing other asset."""
    asset = get_object_or_404(OtherAsset, pk=pk, user=request.user)
    
    if request.method == 'POST':
        asset.name = request.POST.get('name', asset.name).strip()
        asset.asset_type = request.POST.get('asset_type', asset.asset_type)
        purchase_date_str = request.POST.get('purchase_date')
        
        try:
            asset.purchase_price = Decimal(request.POST.get('purchase_price', str(asset.purchase_price)))
            asset.current_value = Decimal(request.POST.get('current_value', str(asset.current_value)))
            asset.monthly_rent = Decimal(request.POST.get('monthly_rent', str(asset.monthly_rent)))
            if purchase_date_str:
                asset.purchase_date = pd.to_datetime(purchase_date_str).date()
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric or date values provided.")
            return redirect('edit_other_asset', pk=pk)

        asset.save()
        messages.success(request, f"Updated Asset: {asset.name}.")
        return redirect('other_assets_dashboard')
        
    return render(request, 'core/other_asset_form.html', {
        'action': 'Edit', 
        'asset': asset, 
        'asset_types': OtherAsset.ASSET_TYPES
    })

@login_required
def delete_other_asset(request, pk):
    """Delete an other asset."""
    asset = get_object_or_404(OtherAsset, pk=pk, user=request.user)
    name = asset.name
    asset.delete()
    messages.success(request, f"Removed {name} from your Other Assets.")
    return redirect('other_assets_dashboard')

# --- LOAN Module ---

def _process_auto_emis(loan):
    """Automatically record EMIs that have passed since the last processed EMI."""
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal
    from datetime import date
    
    today = date.today()
    # Limit iterations to avoid infinite loops in case of bad data
    iterations = 0
    while loan.next_emi_date and today >= loan.next_emi_date and iterations < 360:
        iterations += 1
        
        # Calculate interest component
        if loan.interest_type == 'Flat':
            interest = (loan.loan_amount * loan.interest_rate / 100) / 12
        else:
            # Reducing balance: based on current outstanding
            interest = (loan.current_outstanding * loan.interest_rate / 100) / 12
            
        interest = Decimal(str(interest)).quantize(Decimal('0.01'))
        
        # Principal component is EMI minus interest
        principal = loan.emi_amount - interest
        if principal < 0: principal = 0
        
        # If remaining principal is less than calculated principal, adjust
        cur_out = loan.current_outstanding
        if principal > cur_out:
            principal = cur_out
            # Optional: adjust amount or record as last EMI
            
        LoanPayment.objects.create(
            loan=loan,
            payment_type='EMI',
            amount=loan.emi_amount,
            date=loan.next_emi_date,
            principal_component=principal,
            interest_component=interest
        )
        
        # Update next emi date
        loan.next_emi_date = loan.next_emi_date + relativedelta(months=1)
        
        # If loan is fully paid, stop
        if loan.current_outstanding <= 0:
            loan.is_active = False
            loan.next_emi_date = None
            loan.save()
            break
            
        loan.save()

@login_required
def loan_dashboard(request):
    """Dashboard for all loans."""
    loans = Loan.objects.filter(user=request.user).order_by('-start_date')
    
    # Process auto EMIs before calculating totals
    for l in loans:
        if l.is_active:
            _process_auto_emis(l)
            
    total_loan_amount = float(sum(l.loan_amount for l in loans))
    total_outstanding = float(sum(l.current_outstanding for l in loans))
    total_interest_paid = float(sum(l.total_interest_paid for l in loans))
    total_paid = float(sum(l.total_paid_till_date for l in loans))
    
    context = {
        'loans': loans,
        'total_loan_amount': total_loan_amount,
        'total_outstanding': total_outstanding,
        'total_interest_paid': total_interest_paid,
        'total_paid': total_paid,
        'last_updated': timezone.now(),
    }
    return render(request, 'core/loan_dashboard.html', context)

@login_required
def add_loan(request):
    """Add a new loan."""
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.user = request.user
            loan.save()
            messages.success(request, f"Loan from {loan.bank_name} added successfully.")
            return redirect('loan_dashboard')
    else:
        # Suggest today's date for next EMI
        form = LoanForm(initial={'next_emi_date': timezone.now().date()})
        
    return render(request, 'core/loan_form.html', {'form': form, 'action': 'Add'})

@login_required
def edit_loan(request, pk):
    """Edit an existing loan."""
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    if request.method == 'POST':
        form = LoanForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated loan from {loan.bank_name}.")
            return redirect('loan_dashboard')
    else:
        form = LoanForm(instance=loan)
        
    return render(request, 'core/loan_form.html', {'form': form, 'action': 'Edit'})

@login_required
def delete_loan(request, pk):
    """Delete a loan."""
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    bank = loan.bank_name
    loan.delete()
    messages.success(request, f"Removed loan from {bank}.")
    return redirect('loan_dashboard')

@login_required
def loan_detail(request, pk):
    """Detail view for a loan, showing payment history and breakup."""
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    payments = loan.payments.all().order_by('-date', '-created_at')
    
    # Simple Amortization for UI (next 12 months)
    amortization = []
    temp_outstanding = float(loan.current_outstanding)
    temp_date = loan.next_emi_date or (timezone.now().date() + relativedelta(months=1))
    
    for i in range(12):
        if temp_outstanding <= 0: break
        
        if loan.interest_type == 'Flat':
            interest = (float(loan.loan_amount) * float(loan.interest_rate) / 100) / 12
        else:
            interest = (temp_outstanding * float(loan.interest_rate) / 100) / 12
            
        principal = float(loan.emi_amount) - interest
        if principal > temp_outstanding:
            principal = temp_outstanding
            
        amortization.append({
            'date': temp_date,
            'emi': loan.emi_amount,
            'principal': principal,
            'interest': interest,
            'balance': temp_outstanding - principal
        })
        temp_outstanding -= principal
        temp_date += relativedelta(months=1)

    context = {
        'loan': loan,
        'payments': payments,
        'amortization': amortization,
    }
    return render(request, 'core/loan_detail.html', context)

@login_required
def add_loan_payment(request, pk):
    """Record a prepayment or manual payment."""
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        date_str = request.POST.get('date')
        payment_date = pd.to_datetime(date_str).date() if date_str else timezone.now().date()
        
        # Prepayment logic: typically all goes to principal
        principal = amount
        interest = Decimal('0')
        
        LoanPayment.objects.create(
            loan=loan,
            payment_type='Prepayment',
            amount=amount,
            date=payment_date,
            principal_component=principal,
            interest_component=interest
        )
        
        if loan.current_outstanding <= 0:
            loan.is_active = False
            loan.save()
            
        messages.success(request, f"Recorded prepayment of ₹{amount} for {loan.bank_name} loan.")
        return redirect('loan_detail', pk=pk)
        
    return render(request, 'core/loan_payment_form.html', {'loan': loan})
