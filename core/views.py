from django.shortcuts import render, redirect, get_object_or_404
from django.db import models, transaction as db_transaction
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
from datetime import datetime, timedelta, date
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
    Loan, LoanPayment, IPO, ChatbotKnowledge, Watchlist, Dividend,
    InvestmentGoal, SignalNotificationState, FamilyLink, FinancialYearData,
    MFSIP, PortfolioValueHistory, HiddenSignal, UserReview, NewsAlert, BlogPost, BlogComment
)
from .forms import (
    UploadFileForm, PortfolioForm, ManualPortfolioForm, ManualSellForm,
    CustomUserCreationForm, ProfileForm, ForgotPasswordForm, 
    VerifyOTPForm, SetPasswordForm, EditLotForm,
    LoanForm, LoanPaymentForm, UserReviewForm
)
from .utils import fetch_live_ltp, perform_sync, get_recommendations, fetch_strategy_stocks, get_target_user

import random
import json
import yfinance as yf
import pandas as pd
import math
from decimal import Decimal, InvalidOperation

import logging
logger = logging.getLogger(__name__)

from functools import wraps
from django.db import IntegrityError

def prevent_duplicate_submissions(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.method == 'POST':
            idempotency_key = request.POST.get('idempotency_key')
            if idempotency_key:
                from .models import IdempotencyKey
                try:
                    # Attempt to create the idempotency key in a transaction
                    with db_transaction.atomic():
                        IdempotencyKey.objects.create(key=idempotency_key)
                except IntegrityError:
                    # Key already exists: block duplicate submission
                    messages.warning(request, "This request has already been processed.")
                    try:
                        target_user, is_family_view, _ = get_target_user(request)
                        if is_family_view:
                            return redirect(f"/dashboard/?user_id={target_user.id}")
                    except Exception:
                        pass
                    return redirect('dashboard')
                
                # If key creation succeeded, execute view logic
                try:
                    with db_transaction.atomic():
                        return view_func(request, *args, **kwargs)
                except Exception:
                    # Roll back the idempotency key on failure so it can be retried
                    try:
                        IdempotencyKey.objects.filter(key=idempotency_key).delete()
                    except Exception:
                        pass
                    raise
            else:
                return view_func(request, *args, **kwargs)
        return view_func(request, *args, **kwargs)
    return wrapped_view

@login_required
def portfolio_history_api(request):
    """API for lazy loading portfolio history graph data."""
    from .utils import get_target_user
    target_user, is_family_view, is_consolidated = get_target_user(request)
    from .models import PortfolioValueHistory
    history = PortfolioValueHistory.objects.filter(user=target_user).order_by('date')
    history_data = {
        'dates': [h.date.strftime('%Y-%m-%d') for h in history],
        'net_worth': [float(h.net_worth) for h in history],
        'invested': [float(h.invested_value) for h in history],
    }
    return JsonResponse(history_data)

def _auto_update_mf():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import MutualFund
        from .utils import sync_mutual_funds_from_sheet
        from .mf_utils import sync_fund_from_mfapi
        
        # Sync from Google Sheets first
        sync_mutual_funds_from_sheet()
        
        # Then, sync any manually added funds (which have a scheme_code) that are stale
        two_hours_ago = timezone.now() - timedelta(minutes=120)
        stale_manual_funds = MutualFund.objects.filter(
            scheme_code__isnull=False,
            last_updated__lt=two_hours_ago
        )
        for fund in stale_manual_funds:
            try:
                sync_fund_from_mfapi(fund)
            except Exception as e:
                logger.error(f"Failed to sync manual fund {fund.scheme_code}: {e}")
    except Exception as e:
        logger.error(f"Auto update MF failed: {e}")

def _auto_update_coin():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import Coin
        from .utils import sync_coins_from_sheet
        
        two_hours_ago = timezone.now() - timedelta(minutes=120)
        stale_coins = Coin.objects.filter(last_updated__lt=two_hours_ago)
        if stale_coins.exists():
            sync_coins_from_sheet()
    except Exception as e:
        logger.error(f"Auto update Coin failed: {e}")

def _auto_update_nps():
    try:
        from django.utils import timezone
        from datetime import timedelta
        from .models import NPSFund
        from .utils import sync_nps_from_sheet
        
        two_hours_ago = timezone.now() - timedelta(minutes=120)
        stale_funds = NPSFund.objects.filter(last_updated__lt=two_hours_ago)
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
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        
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
            user = User.objects.get(email__iexact=email)
            
            # Generate 6-digit OTP
            code = str(random.randint(100000, 999999))
            
            # Save OTP
            OTP.objects.filter(user=user).delete() # Delete old ones
            OTP.objects.create(user=user, code=code)
            
            # Send Email
            try:
                subject = "Your Password Reset Code"
                message = f"Your 6-digit verification code is: {code}\nThis code is valid for 10 minutes."
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                
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
            user = User.objects.get(email__iexact=email)
            # Fetch latest OTP for user (code is encrypted, so we compare in memory)
            otp_obj = OTP.objects.filter(user=user).order_by('-created_at').first()
            
            if otp_obj:
                stored_code = str(otp_obj.code).strip()
                input_code = str(otp_code).strip()
                is_expired = not otp_obj.is_valid()
                
                if stored_code == input_code and not is_expired:
                    request.session['otp_verified'] = True
                    return redirect('reset_password')
                else:
                    logger.warning(f"OTP verification failed for {email}: Match={stored_code == input_code}, Expired={is_expired}")
            else:
                logger.warning(f"No OTP found for user {email}")
            
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

@csrf_exempt
def google_one_tap_login(request):
    """
    Backend handler for Google One Tap login.
    Verifies the JWT token and authenticates/creates the user.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    credential = request.POST.get('credential')
    if not credential:
        return JsonResponse({'status': 'error', 'message': 'No credential provided'}, status=400)

    try:
        # Verify the token with Google's tokeninfo service
        # Alternatively, use google-auth library if available: id_token.verify_oauth2_token
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={credential}', timeout=10)
        
        if response.status_code != 200:
            return JsonResponse({'status': 'error', 'message': 'Invalid token'}, status=400)

        id_info = response.json()

        # Check AUD (Google Client ID)
        if id_info.get('aud') != settings.GOOGLE_CLIENT_ID:
            return JsonResponse({'status': 'error', 'message': 'Invalid audience'}, status=400)

        email = id_info.get('email')
        first_name = id_info.get('given_name', '')
        last_name = id_info.get('family_name', '')
        
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email not provided by Google'}, status=400)

        # Get or Create User
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            # Create user if it doesn't exist
            username = email.split('@')[0]
            # Handle username collisions
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            # Create profile if needed (assuming Profile is created via signals, 
            # but some systems might need manual creation if signals are not set up)
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user)
        
        # Link social account if using django-allauth
        try:
            from allauth.socialaccount.models import SocialAccount, SocialApp
            from allauth.socialaccount.providers.google.provider import GoogleProvider
            
            social_app = SocialApp.objects.filter(provider=GoogleProvider.id).first()
            if social_app:
                SocialAccount.objects.get_or_create(
                    user=user,
                    provider=GoogleProvider.id,
                    uid=id_info.get('sub'),
                    defaults={'extra_data': id_info}
                )
        except (ImportError, Exception) as e:
            logger.warning(f"Failed to link social account: {e}")

        # Login User
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        # Ensure session age is honored
        if not request.POST.get('remember') == 'false':
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        # Resolve redirect URL
        next_url = request.POST.get('next')
        if next_url and next_url.startswith('/'):
            redirect_url = next_url
        else:
            from django.urls import reverse
            try:
                redirect_url = reverse(settings.LOGIN_REDIRECT_URL)
            except:
                redirect_url = '/'
            
        return JsonResponse({'status': 'success', 'redirect_url': redirect_url})

    except Exception as e:
        logger.error(f"Google One Tap Login Error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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
# Optional headers: 'Date'
PNL_HEADERS = ['Symbol', 'Quantity', 'Buy Value', 'Sell Value', 'Profit', 'Entry Date', 'Exit Date']
TRADE_HEADERS = ['Symbol', 'Trade Date', 'Trade Type', 'Quantity', 'Price']

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
    if f.name.endswith('.csv') or f.name.endswith('.txt') or f.name.endswith('.tsv'):
        return pd.read_csv(f, sep=None, engine='python')
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
            'percent_change': t.percent_change,
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

def fetch_landing_data(force_fetch=False):
    """Fetch all RSS feeds for the landing page with caching."""
    cache_key = 'landing_rss_data_v3'  # v3: Livemint + Zerodha Pulse
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    if not force_fetch:
        # If cache miss, attempt a quick fallback fetch with 2s timeout to avoid blank landing pages.
        logger.info("RSS feed cache miss; performing quick fallback fetch.")
        try:
            nse_news = fetch_rss_feed('https://www.livemint.com/rss/markets', 'Livemint', timeout=2)
            pulse_news = fetch_rss_feed('http://pulse.zerodha.com/feed.php', 'Zerodha Pulse', timeout=2)
            result = {
                'nse_news': nse_news[:20],
                'financial_news': pulse_news[:20]
            }
            if nse_news or pulse_news:
                cache.set(cache_key, result, 86400) # 24 hours cache TTL
                return result
        except Exception as e:
            logger.error(f"Quick fallback RSS fetch failed: {e}")
        
        return {
            'nse_news': [],
            'financial_news': []
        }

    # Left tile: Livemint Markets RSS
    nse_news = fetch_rss_feed('https://www.livemint.com/rss/markets', 'Livemint')
    
    # Financial News - Zerodha Pulse
    pulse_news = fetch_rss_feed('http://pulse.zerodha.com/feed.php', 'Zerodha Pulse')
    
    result = {
        'nse_news': nse_news[:20],
        'financial_news': pulse_news[:20]
    }
    
    if nse_news or pulse_news:
        cache.set(cache_key, result, 86400) # 24 hours cache TTL, refreshed every 30 mins by background scheduler
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
        'reviews': UserReview.objects.filter(is_public=True),
        'news_alerts': NewsAlert.objects.all().order_by('-news_date', '-created_at')[:15],
        'last_updated': datetime.datetime.now(),
    }
    return render(request, 'core/landing.html', context)

@login_required
def submit_review(request):
    if request.method == 'POST':
        form = UserReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.save()
            messages.success(request, "Thank you for your feedback!")
            return redirect('landing')
    else:
        form = UserReviewForm()
    return render(request, 'core/feedback.html', {'form': form})

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
    
    target_user, is_family_view, is_consolidated = get_target_user(request)
    if request.user.is_authenticated:
        # Get all symbols from strategy marquees
        all_strategy_symbols = set()
        symbol_to_strategy = {}
        
        user_ids = [target_user.id]
        if is_consolidated:
            from .utils import get_consolidated_users
            user_ids = get_consolidated_users(request.user)
            
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
            user_id__in=user_ids, 
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
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
        'flexi_stocks': strategy_stocks.get('flexi', []),
        'quant_stocks': strategy_stocks.get('quant', []),
        'pyramid_stocks': strategy_stocks.get('pyramid', []),
        'growth_stocks': strategy_stocks.get('growth', []),
        'others_stocks': others_stocks,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'has_investments': has_investments,
        'default_backtest_date': (timezone.now() - relativedelta(years=5)).strftime('%Y-%m-%d'),
    }
    return render(request, 'core/strategy.html', context)

def mf_guide(request):
    """Mutual Fund Guide page - redirects authenticated users to dashboard."""
    if request.user.is_authenticated:
        return redirect('mf_dashboard')
    return render(request, 'core/mf_guide.html')

def _process_auto_mf_sips(user):
    """Automatically record Mutual Fund SIPs that have passed since the last execution."""
    from .models import MFSIP, MFTransaction, MFPortfolio
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal
    from datetime import date
    from django.utils import timezone
    
    today = timezone.localdate()
    active_sips = MFSIP.objects.filter(user=user, is_active=True, next_execution_date__lte=today)
    
    for sip in active_sips:
        # Limit iterations to avoid infinite loops if it's been many months
        iterations = 0
        while sip.next_execution_date and today >= sip.next_execution_date and iterations < 120:
            iterations += 1
            
            # Fetch current NAV or fallback to last known
            nav = sip.fund.nav or Decimal('0')
            if nav <= 0:
                # If NAV is 0, we can't reliably buy. Skip for now.
                break
                
            units_to_buy = sip.amount / nav
            
            # Record Transaction
            MFTransaction.objects.create(
                user=user,
                fund=sip.fund,
                transaction_type='BUY',
                units=units_to_buy,
                remaining_units=units_to_buy,
                price=nav,
                date=sip.next_execution_date
            )
            
            # Update Portfolio
            portfolio, created = MFPortfolio.objects.get_or_create(
                user=user, fund=sip.fund,
                defaults={'units': 0, 'avg_nav': 0}
            )
            
            total_units = portfolio.units + units_to_buy
            new_avg_nav = ((portfolio.units * portfolio.avg_nav) + (units_to_buy * nav)) / total_units
            portfolio.units = total_units
            portfolio.avg_nav = new_avg_nav
            portfolio.save()
            
            # Update next execution date
            sip.last_executed_at = timezone.now()
            sip.next_execution_date = sip.next_execution_date + relativedelta(months=1)
            sip.save()

@login_required
def mf_dashboard(request):
    """Isolated dashboard for Mutual Funds with SIP processing."""
    # Trigger auto update if data is stale in background thread
    import threading
    def _run_bg_mf():
        try:
            _auto_update_mf()
        except Exception:
            pass
    threading.Thread(target=_run_bg_mf, daemon=True).start()
    target_user, is_family_view, is_consolidated = get_target_user(request)
    _process_auto_mf_sips(target_user)
    
    if is_consolidated:
        from .utils import get_consolidated_users
        user_ids = get_consolidated_users(request.user)
        all_holdings_qs = MFPortfolio.objects.filter(user_id__in=user_ids).select_related('fund')
        
        # Aggregate by fund
        agg_map = {}
        for h in all_holdings_qs:
            fid = h.fund_id
            if fid not in agg_map:
                # Copy properties to a simple object/dict structure
                agg_map[fid] = {
                    'fund': h.fund,
                    'units': Decimal('0'),
                    'invested_amount': Decimal('0'),
                    'realized_profit': Decimal('0'),
                }
            agg_map[fid]['units'] += h.units
            agg_map[fid]['invested_amount'] += h.invested_amount
            agg_map[fid]['realized_profit'] += h.realized_profit
        
        # Convert aggregated map to a list of mock objects for template compatibility
        mf_holdings = []
        class MockMFPortfolio:
            def __init__(self, data):
                self.fund = data['fund']
                self.fund_id = data['fund'].id
                self.units = data['units']
                self.invested_amount = data['invested_amount']
                self.realized_profit = data['realized_profit']
                self.avg_nav = self.invested_amount / self.units if self.units > 0 else 0
            @property
            def current_value(self): return self.units * self.fund.nav
            @property
            def unrealized_pnl(self): return self.current_value - self.invested_amount
            @property
            def pnl_percentage(self): return (self.unrealized_pnl / self.invested_amount * 100) if self.invested_amount > 0 else 0
            @property
            def day_change(self): 
                if self.fund.prev_nav == 0: return 0
                return self.units * (self.fund.nav - self.fund.prev_nav)

        for fid, data in agg_map.items():
            if data['units'] > 0:
                mf_holdings.append(MockMFPortfolio(data))
    else:
        all_holdings = MFPortfolio.objects.filter(user=target_user).select_related('fund')
        mf_holdings = [h for h in all_holdings if h.units > 0]

    total_invested = sum(h.invested_amount for h in mf_holdings)
    total_current_value = sum(h.current_value for h in mf_holdings)
    total_unrealized_pnl = total_current_value - total_invested
    total_realized_profit = sum(h.realized_profit for h in mf_holdings)
    total_day_change = sum(h.day_change for h in mf_holdings)
    total_pnl_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
    
    # Fetch active SIPs for this user
    from .models import MFSIP
    active_sips = {sip.fund_id: sip for sip in MFSIP.objects.filter(user=request.user, is_active=True)}
    
    # Process advice and attach SIP data for each holding
    mf_limit = target_user.profile.mf_investment_limit
    for h in mf_holdings:
        h.active_sip = active_sips.get(h.fund_id)
        h.advice = []
        mf_profit_target = float(target_user.profile.mf_profit_expectation)
        # Suppress SELL if Realized Profit > Current Investment (keep averaging instead)
        if h.pnl_percentage >= mf_profit_target and h.realized_profit <= h.invested_amount:
            h.advice.append({'type': 'SELL', 'reason': f'Target {mf_profit_target}% reached ({float(h.pnl_percentage):.2f}%)'})
        
        target = mf_limit + h.realized_profit
        if h.invested_amount < target:
            gap = target - h.invested_amount
            h.advice.append({'type': 'BUY', 'reason': f'Target ₹{float(target):,.0f} (Gap ₹{float(gap):,.0f})'})
        elif h.invested_amount > target + Decimal('3000'):
            excess = h.invested_amount - target
            h.advice.append({'type': 'REDUCE', 'reason': f'Excess of ₹{float(excess):,.0f} over target ₹{float(target):,.0f}'})

    context = {
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
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
def mf_detail(request, pk):
    """View details and performance graph for a mutual fund."""
    fund = get_object_or_404(MutualFund, pk=pk)
    
    # If no scheme_code, try to find it by name if it's a new integration
    if not fund.scheme_code:
        try:
            from core.models import MutualFundScheme
            from django.db.models import Q
            scheme = MutualFundScheme.objects.filter(
                Q(scheme_name__icontains=fund.name) | Q(scheme_code=fund.name)
            ).first()
            if scheme:
                fund.scheme_code = scheme.scheme_code
                fund.save()
        except Exception as e:
            logger.error(f"Error finding scheme_code locally: {e}")
            
    history = fund.get_nav_history()
    
    # Prepare data for Chart.js
    chart_data = {
        'labels': [h['date'] for h in reversed(history[:250])], # Last 250 days
        'navs': [float(h['nav']) for h in reversed(history[:250])]
    }
    
    context = {
        'fund': fund,
        'chart_data': json.dumps(chart_data),
        'latest_nav': history[0] if history else None,
    }
    return render(request, 'core/mf_detail.html', context)

@login_required
@prevent_duplicate_submissions
def add_mf_portfolio(request):
    """Add a mutual fund holding manually."""
    if request.method == 'POST':
        target_user, is_family_view, is_consolidated = get_target_user(request)
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
        fund = MutualFund.objects.filter(symbol=symbol).first()
        if not fund:
            # Check if symbol is a numeric scheme code
            if symbol.isdigit():
                fund = MutualFund.objects.filter(scheme_code=symbol).first()
        
        if not fund:
            fund = MutualFund(symbol=symbol)
            if symbol.isdigit():
                fund.scheme_code = symbol
            fund.save()
            created = True
        else:
            created = False

        if created or fund.nav == 0:
            # Try mfapi.in first if it's a numeric code
            if fund.scheme_code:
                from .mf_utils import get_mf_details
                details = get_mf_details(fund.scheme_code)
                if details and details.get('data'):
                    fund.nav = Decimal(str(details['data'][0]['nav']))
                    fund.name = details.get('meta', {}).get('scheme_name', fund.name)
                    fund.amc = details.get('meta', {}).get('fund_house', fund.amc)
                    fund.save()
            
            # Fallback to yfinance if NAV still 0
            if fund.nav == 0:
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    nav_val = info.get('regularMarketPrice') or info.get('navPrice') or info.get('previousClose')
                    if nav_val:
                        fund.nav = Decimal(str(nav_val))
                    else:
                        fund.nav = avg_nav # Fallback to avg_nav
                    fund.name = info.get('longName') or fund.name or symbol
                    fund.save()
                except Exception as e:
                    logger.error(f"Error fetching NAV for {symbol}: {e}")
                    if created: 
                        fund.name = fund.name or symbol
                        fund.nav = avg_nav
                        fund.save()

        # Update or create MFPortfolio item
        portfolio_item, p_created = MFPortfolio.objects.get_or_create(
            user=target_user, fund=fund,
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
                user=target_user,
                fund=fund,
                transaction_type='BUY',
                units=units,
                remaining_units=units,
                price=avg_nav,
                date=timezone.localdate()
            )
            
        # If SIP is enabled, create MFSIP record
        is_sip = request.POST.get('is_sip') == 'on'
        if is_sip:
            sip_amount = Decimal(request.POST.get('sip_amount', '0'))
            sip_date_day = int(request.POST.get('sip_date', '5'))
            
            # Calculate first next execution date
            from datetime import date
            from dateutil.relativedelta import relativedelta
            today = date.today()
            
            # If today's day is already past the SIP day, start from next month
            # Otherwise, use this month's date
            try:
                next_date = date(today.year, today.month, sip_date_day)
                if next_date <= today:
                    next_date = next_date + relativedelta(months=1)
            except ValueError:
                # Handle cases like 31st on a 30-day month
                next_date = date(today.year, today.month, 28) + relativedelta(months=1)
                next_date = date(next_date.year, next_date.month, min(sip_date_day, 28))

            from .models import MFSIP
            MFSIP.objects.get_or_create(
                user=target_user,
                fund=fund,
                defaults={
                    'amount': sip_amount,
                    'sip_date': sip_date_day,
                    'next_execution_date': next_date,
                    'is_active': True
                }
            )
            messages.info(request, f"Monthly SIP of ₹{sip_amount} scheduled on {sip_date_day}th of every month.")

        messages.success(request, f"Successfully added {fund.name} to your Mutual Fund portfolio.")
        return redirect('mf_dashboard')
        
    prefill_symbol = request.GET.get('symbol', '')
    return render(request, 'core/mf_add_item.html', {'prefill_symbol': prefill_symbol})

@login_required
@prevent_duplicate_submissions
def sell_mf_portfolio(request, pk):
    target_user, is_family_view, is_consolidated = get_target_user(request)
    holding = get_object_or_404(MFPortfolio, pk=pk, user=target_user)
    if request.method == 'POST':
        try:
            units_to_sell = Decimal(request.POST.get('units', '0'))
            sell_price = Decimal(request.POST.get('price', '0'))
            sell_date_str = request.POST.get('date')
            sell_date = pd.to_datetime(sell_date_str).date() if sell_date_str else timezone.localdate()
            if sell_date > timezone.localdate():
                messages.error(request, "Date cannot be in the future.")
                return redirect('mf_dashboard')
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
            user=target_user,
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
    """Fetch latest NAVs for all funds by triggering a master sync from Google Sheets and mfapi.in."""
    from .utils import sync_mutual_funds_from_sheet
    from .mf_utils import sync_fund_from_mfapi
    from .models import MutualFund
    
    try:
        count = sync_mutual_funds_from_sheet()
        
        # Sync all manually added funds (which have a scheme_code)
        manual_funds = MutualFund.objects.filter(scheme_code__isnull=False)
        manual_count = 0
        for fund in manual_funds:
            try:
                if sync_fund_from_mfapi(fund):
                    manual_count += 1
            except Exception as e:
                logger.error(f"Manual refresh failed for fund {fund.scheme_code}: {e}")
                
        total_count = count + manual_count
        if total_count > 0:
            messages.success(request, f"Synced {total_count} Mutual Funds with latest NAVs (Sheets: {count}, Manual: {manual_count}).")
        else:
            messages.info(request, "Mutual fund sync completed.")
    except Exception as e:
        logger.error(f"Manual MF refresh failed: {e}")
        messages.error(request, "Failed to refresh Mutual Fund NAVs.")
        
    return redirect('mf_dashboard')

# --- COIN (Crypto) Module ---

@login_required
def coin_dashboard(request):
    """Dashboard for Cryptocurrency holdings using FIFO."""
    # Trigger auto update if data is stale in background thread
    import threading
    def _run_bg_coin():
        try:
            _auto_update_coin()
        except Exception:
            pass
    threading.Thread(target=_run_bg_coin, daemon=True).start()
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    if is_consolidated:
        from .utils import get_consolidated_users
        user_ids = get_consolidated_users(request.user)
        all_holdings_qs = CoinPortfolio.objects.filter(user_id__in=user_ids).select_related('coin')
        
        # Aggregate by coin
        agg_map = {}
        for h in all_holdings_qs:
            cid = h.coin_id
            if cid not in agg_map:
                agg_map[cid] = {
                    'coin': h.coin,
                    'units': Decimal('0'),
                    'invested_amount': Decimal('0'),
                    'realized_profit': Decimal('0'),
                }
            agg_map[cid]['units'] += h.units
            agg_map[cid]['invested_amount'] += h.invested_amount
            agg_map[cid]['realized_profit'] += h.realized_profit
            
        coin_holdings = []
        class MockCoinPortfolio:
            def __init__(self, data):
                self.coin = data['coin']
                self.coin_id = data['coin'].id
                self.units = data['units']
                self.invested_amount = data['invested_amount']
                self.realized_profit = data['realized_profit']
                self.avg_price = self.invested_amount / self.units if self.units > 0 else 0
            @property
            def current_value(self): return self.units * self.coin.price
            @property
            def unrealized_pnl(self): return self.current_value - self.invested_amount
            @property
            def pnl_percentage(self): return (self.unrealized_pnl / self.invested_amount * 100) if self.invested_amount >0 else 0
            @property
            def day_change(self):
                if self.coin.prev_price == 0: return 0
                return self.units * (self.coin.price - self.coin.prev_price)
        
        for cid, data in agg_map.items():
            if data['units'] > 0:
                coin_holdings.append(MockCoinPortfolio(data))
    else:
        all_holdings = CoinPortfolio.objects.filter(user=target_user).select_related('coin')
        coin_holdings = [h for h in all_holdings if h.units > 0]
        
    total_invested = sum(h.invested_amount for h in coin_holdings)
    total_current_value = sum(h.current_value for h in coin_holdings)
    total_unrealized_pnl = total_current_value - total_invested
    total_realized_profit = sum(h.realized_profit for h in coin_holdings)
    total_day_change = sum(h.day_change for h in coin_holdings)
    total_pnl_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
    
    coin_limit = target_user.profile.coin_investment_limit
    for h in coin_holdings:
        h.advice = []
        coin_profit_target = float(target_user.profile.coin_profit_expectation)
        # Suppress SELL if Realized Profit > Current Investment (keep averaging instead)
        if h.pnl_percentage >= coin_profit_target and h.realized_profit <= h.invested_amount:
            h.advice.append({'type': 'SELL', 'reason': f'Profit {float(h.pnl_percentage):.2f}% >= {coin_profit_target}%'})
        
        # Crypto target: user defined (default 15k)
        target = coin_limit + h.realized_profit
        if h.invested_amount < target:
            gap = target - h.invested_amount
            h.advice.append({'type': 'BUY', 'reason': f'Target ₹{float(target):,.0f} (Gap ₹{float(gap):,.0f})'})
        elif h.invested_amount > target + Decimal('3000'):
            excess = h.invested_amount - target
            h.advice.append({'type': 'REDUCE', 'reason': f'Excess of ₹{float(excess):,.0f} over target ₹{float(target):,.0f}'})
    
    context = {
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
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
def coin_detail(request, pk):
    """View details and performance graph for a cryptocurrency."""
    coin = get_object_or_404(Coin, pk=pk)
    history = coin.get_price_history()
    
    # Prepare data for Chart.js
    chart_data = {
        'labels': [h['date'] for h in history],
        'prices': [h['price'] for h in history]
    }
    
    context = {
        'coin': coin,
        'chart_data': json.dumps(chart_data),
        'latest_price': history[-1] if history else None,
    }
    return render(request, 'core/coin_detail.html', context)


@login_required
@prevent_duplicate_submissions
def add_coin(request):
    """Add a cryptocurrency holding manually."""
    target_user, is_family_view, is_consolidated = get_target_user(request)
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
            
        # Sync first to ensure we have latest from sheet
        from .utils import sync_coins_from_sheet
        sync_coins_from_sheet()
        
        # Now try to find the coin
        coin = Coin.objects.filter(symbol__iexact=symbol).first()
        if not coin:
            # Try plain symbol if symbol-INR was used
            plain_symbol = symbol.split('-')[0]
            coin = Coin.objects.filter(symbol__iexact=plain_symbol).first()
        
        if not coin:
            # Fallback: create even if not in sheet (though it won't get price updates)
            coin, _ = Coin.objects.get_or_create(
                symbol=symbol,
                defaults={'name': symbol, 'price': avg_price}
            )

        holding, h_created = CoinPortfolio.objects.get_or_create(
            user=target_user, 
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
            user=target_user,
            coin=coin,
            transaction_type='BUY',
            units=units,
            remaining_units=units,
            price=avg_price,
            date=timezone.localdate()
        )
        
        messages.success(request, f"Added {units} units of {coin.name} for {target_user.username if is_family_view else 'account'}.")
        url = redirect('coin_dashboard').url
        if is_family_view:
            url += f"?user_id={target_user.id}"
        return redirect(url)
        
    return render(request, 'core/coin_add_item.html', {
        'is_family_view': is_family_view,
        'target_user': target_user
    })

@login_required
@prevent_duplicate_submissions
def sell_coin(request, pk):
    """Sell a cryptocurrency holding using FIFO."""
    target_user, is_family_view, is_consolidated = get_target_user(request)
    holding = get_object_or_404(CoinPortfolio, pk=pk, user=target_user)
    if request.method == 'POST':
        try:
            units_to_sell = Decimal(request.POST.get('units', '0'))
            sell_price = Decimal(request.POST.get('price', '0'))
            sell_date_str = request.POST.get('date')
            sell_date = pd.to_datetime(sell_date_str).date() if sell_date_str else timezone.localdate()
            if sell_date > timezone.localdate():
                messages.error(request, "Date cannot be in the future.")
                return redirect('coin_dashboard')
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
            user=target_user,
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
            user=target_user,
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
            user=target_user,
            coin=holding.coin,
            transaction_type='SELL',
            units=units_to_sell,
            price=sell_price,
            date=sell_date
        )
        
        messages.success(request, f"Sold {units_to_sell} units of {holding.coin.name} for {target_user.username if is_family_view else 'account'}. Profit: ₹{float(profit):,.2f}")
        url = redirect('coin_dashboard').url
        if is_family_view:
            url += f"?user_id={target_user.id}"
        return redirect(url)
        
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
    """Fetch latest prices for all crypto coins using the Google Spreadsheet sync."""
    from .utils import sync_coins_from_sheet
    try:
        count = sync_coins_from_sheet()
        if count > 0:
            messages.success(request, f"Coin prices refreshed from spreadsheet ({count} updated).")
        else:
            messages.warning(request, "Spreadsheet sync completed, no updates found.")
    except Exception as e:
        messages.error(request, f"Failed to refresh prices: {e}")
        
    return redirect('coin_dashboard')

@login_required
def portfolio(request):
    """Broad portfolio summary view for all asset classes."""
    # Ensure asset data is fresh (lazy sync) in a background thread to prevent blocking
    import threading
    def _run_bg_sync():
        try:
            _auto_update_mf()
            _auto_update_coin()
            _auto_update_nps()
        except Exception:
            pass
    
    threading.Thread(target=_run_bg_sync, daemon=True).start()
    
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    user_ids = [target_user.id]
    if is_consolidated:
        from .utils import get_consolidated_users
        user_ids = get_consolidated_users(request.user)
    
    # Portfolio history for chart
    
    # Process any background tasks
    _process_auto_mf_sips(target_user)
    # 1. Stocks/ETF
    recommendations, realized_profits, _ = get_recommendations(target_user, is_consolidated=is_consolidated)
    stocks_recs = [r for r in recommendations if r.get('in_portfolio', False)]
    stocks_invested = float(sum(r.get('invested_amount', 0) for r in stocks_recs))
    stocks_current = float(sum(r.get('current_value', 0) for r in stocks_recs))
    stocks_unrealized = stocks_current - stocks_invested
    stocks_realized = float(sum(realized_profits.values()) if isinstance(realized_profits, dict) else 0)

    # 2. Mutual Funds
    mf_holdings = MFPortfolio.objects.filter(user_id__in=user_ids).select_related('fund')
    mf_invested = float(sum(h.invested_amount for h in mf_holdings))
    mf_current = float(sum(h.current_value for h in mf_holdings))
    mf_unrealized = mf_current - mf_invested
    mf_realized = float(sum(h.realized_profit for h in mf_holdings))

    # 3. Coin (Crypto)
    coin_holdings = CoinPortfolio.objects.filter(user_id__in=user_ids).select_related('coin')
    coin_invested = float(sum(h.invested_amount for h in coin_holdings))
    coin_current = float(sum(h.current_value for h in coin_holdings))
    coin_unrealized = coin_current - coin_invested
    coin_realized = float(sum(h.realized_profit for h in coin_holdings))

    # 4. NPS
    nps_holdings = NPSPortfolio.objects.filter(user_id__in=user_ids).select_related('fund')
    nps_invested = float(sum(h.invested_amount for h in nps_holdings))
    nps_current = float(sum(h.current_value for h in nps_holdings))
    nps_unrealized = nps_current - nps_invested
    nps_realized = float(sum(h.realized_profit for h in nps_holdings))

    # 5. Fixed Assets
    fd_invested = fd_current = fd_unrealized = fd_percentage = 0.0
    try:
        fd_holdings = FixedAsset.objects.filter(user_id__in=user_ids)
        fd_invested = float(sum(h.invested_amount_decimal for h in fd_holdings))
        fd_current = float(sum(h.current_value for h in fd_holdings))
        fd_unrealized = float(sum(h.unrealized_pnl for h in fd_holdings))
        if fd_invested > 0:
            fd_percentage = (fd_unrealized / fd_invested) * 100
    except Exception:
        pass

    # 6. Other Assets (Real Estate, Gold, etc)
    other_invested = other_current = other_unrealized = other_percentage = 0.0
    try:
        other_holdings = OtherAsset.objects.filter(user_id__in=user_ids)
        other_invested = float(sum(h.purchase_price for h in other_holdings))
        other_current = float(sum(h.current_value for h in other_holdings))
        other_unrealized = float(sum(h.unrealized_pnl for h in other_holdings))
        if other_invested > 0:
            other_percentage = (other_unrealized / other_invested) * 100
    except Exception:
        pass

    # 7. Loans
    # Process any background tasks for loans and RDs
    _process_auto_mf_sips(target_user)
    _process_auto_rd_deposits(target_user)
    
    loans = Loan.objects.filter(user_id__in=user_ids, is_active=True)
    for l in loans:
        _process_auto_emis(l)
    
    loan_taken = float(sum(l.loan_amount_decimal for l in loans))
    loan_outstanding = float(sum(l.current_outstanding for l in loans))
    
    # Calculate upcoming EMIs (due in next 7 days)
    from datetime import timedelta
    next_week = timezone.localdate() + timedelta(days=7)
    upcoming_emis_count = loans.filter(next_emi_date__lte=next_week, next_emi_date__isnull=False).count()

    # Calculate Totals
    total_investment_cost = stocks_invested + mf_invested + coin_invested + nps_invested + fd_invested + other_invested
    # USER REQUEST: Deduct loan outstanding from Current Value
    total_latest_value = (stocks_current + mf_current + coin_current + nps_current + fd_current + other_current) - loan_outstanding
    total_unrealized_gain = total_latest_value + loan_outstanding - total_investment_cost
    total_realized_gain = stocks_realized + mf_realized + coin_realized + nps_realized
    total_other_gain = 0  # Placeholder for future models

    # Actionable Signals Calculation
    # 1. Stocks & ETFs (Broad Logic - matching dashboard recommendations)
    buy_count = sum(1 for r in recommendations if r.get('action') == 'BUY')
    sell_count = sum(1 for r in recommendations if r.get('action') == 'SELL')
    reduce_count = sum(1 for r in recommendations if r.get('action') == 'REDUCE')

    # 2. Mutual Funds advice
    mf_buy_count = 0
    mf_redemption_count = 0
    mf_reduce_count = 0
    mf_profit_target = float(target_user.profile.mf_profit_expectation)
    mf_limit = target_user.profile.mf_investment_limit
    for h in mf_holdings:
        # Suppress SELL if Realized Profit > Current Investment
        if h.pnl_percentage >= mf_profit_target and h.realized_profit <= h.invested_amount:
            mf_redemption_count += 1
            
        target = mf_limit + h.realized_profit
        if h.invested_amount < target:
            mf_buy_count += 1
        elif h.invested_amount > target + Decimal('3000'):
            mf_reduce_count += 1
                
    # 3. Coin advice (Simple 22% rule for now)
    coin_buy_count = 0
    coin_sell_count = 0
    coin_reduce_count = 0
    coin_profit_target = float(target_user.profile.coin_profit_expectation)
    coin_limit = target_user.profile.coin_investment_limit
    for h in coin_holdings:
        # Suppress SELL if Realized Profit > Current Investment
        if h.pnl_percentage >= coin_profit_target and h.realized_profit <= h.invested_amount:
            coin_sell_count += 1
        
        # Crypto target: user defined (default 15k)
        target = coin_limit + h.realized_profit
        if h.invested_amount < target:
            coin_buy_count += 1
        elif h.invested_amount > target + Decimal('3000'):
            coin_reduce_count += 1

    total_signal_count = buy_count + reduce_count + sell_count + mf_buy_count + mf_redemption_count + mf_reduce_count + coin_buy_count + coin_sell_count + coin_reduce_count

    # 8. Portfolio History Data will now be loaded via API

    # Get all verified family links for switching
    from .models import FamilyLink
    linked_family = FamilyLink.objects.filter(user=request.user, is_verified=True).select_related('family_user__profile')

    context = {
        'linked_family': linked_family,
        'target_user': target_user,
        'is_family_view': is_family_view,
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
        'total_investment_cost': total_investment_cost,
        'total_latest_value': total_latest_value,
        'total_unrealized_gain': total_unrealized_gain,
        'total_realized_gain': total_realized_gain,
        'action_count': total_signal_count,
        'buy_count': buy_count,
        'sell_count': sell_count,
        'reduce_count': reduce_count,
        'mf_buy_count': mf_buy_count,
        'mf_redemption_count': mf_redemption_count,
        'mf_reduce_count': mf_reduce_count,
        'coin_buy_count': coin_buy_count,
        'coin_sell_count': coin_sell_count,
        'coin_reduce_count': coin_reduce_count,
    }
    return render(request, 'core/portfolio.html', context)

def etf_guide(request):
    """ETF Guide page."""
    return render(request, 'core/etf_guide.html')

def nps_guide(request):
    """NPS Guide page."""
    return render(request, 'core/nps_guide.html')

def stock_guide(request):
    """Stock Market Guide page."""
    return render(request, 'core/stock_guide.html')

def education_hub(request):
    """Education Hub landing page displaying blogs and guides."""
    from django.db.models import Q
    from django.core.paginator import Paginator

    # Get search query & tag filter
    search_query = request.GET.get('q', '').strip()
    tag_filter = request.GET.get('tag', '').strip()

    # Get all published posts
    posts = BlogPost.objects.filter(status='published').order_by('-created_at')

    # Apply search filter
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(tags__icontains=search_query)
        )

    # Apply tag filter
    if tag_filter:
        posts = posts.filter(tags__icontains=tag_filter)

    # Get all unique tags for filtering in UI
    all_tags = set()
    for blog in BlogPost.objects.filter(status='published').values_list('tags', flat=True):
        if blog:
            for t in blog.split(','):
                cleaned = t.strip()
                if cleaned:
                    all_tags.add(cleaned)

    # Pagination: 6 posts per page
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'all_tags': sorted(list(all_tags)),
        'search_query': search_query,
        'selected_tag': tag_filter,
    }
    return render(request, 'core/education_hub.html', context)


def blog_detail(request, slug):
    """View to show detailed blog post content."""
    from django.shortcuts import get_object_or_404
    from django.db.models import F

    # Fetch blog post
    post = get_object_or_404(BlogPost, slug=slug)

    # If it is draft, restrict access to staff/superusers only
    if post.status == 'draft' and not request.user.is_staff:
        from django.http import Http404
        raise Http404("This blog post is not yet published.")

    # Increment view count
    BlogPost.objects.filter(id=post.id).update(views_count=F('views_count') + 1)
    post.refresh_from_db()

    # Fetch related posts (sharing any tags, excluding current post)
    related_posts = BlogPost.objects.exclude(id=post.id).filter(status='published')
    tags_list = post.get_tags_list()
    if tags_list:
        from django.db.models import Q
        tag_queries = Q()
        for t in tags_list:
            tag_queries |= Q(tags__icontains=t)
        related_posts = related_posts.filter(tag_queries)
    related_posts = related_posts.order_by('-created_at')[:3]

    # If not enough related posts, backfill with recent posts
    if related_posts.count() < 3:
        exclude_ids = [post.id] + [p.id for p in related_posts]
        extra_posts = BlogPost.objects.exclude(id__in=exclude_ids).filter(status='published').order_by('-created_at')[:3 - related_posts.count()]
        related_posts = list(related_posts) + list(extra_posts)

    context = {
        'post': post,
        'related_posts': related_posts[:3],
    }
    return render(request, 'core/blog_detail.html', context)


@login_required
def add_blog_comment(request, slug):
    """View to add a comment to a blog post."""
    post = get_object_or_404(BlogPost, slug=slug)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            BlogComment.objects.create(post=post, user=request.user, content=content)
            messages.success(request, "Your comment has been posted successfully!")
        else:
            messages.error(request, "Comment content cannot be empty.")
    return redirect(f"{post.get_absolute_url()}?show_comments=true")




def stock_news_list(request):
    """View to list all stock news alerts in a dedicated page."""
    news_alerts = NewsAlert.objects.all().order_by('-news_date', '-created_at')[:50]
    return render(request, 'core/news_list.html', {'news_alerts': news_alerts})


def ipo_list(request):
    """IPO list page for users."""
    from .models import IPO
    target_user, is_family_view, is_consolidated = get_target_user(request) if request.user.is_authenticated else (None, False, False)
    
    ipos = IPO.objects.all().order_by('-start_date')
    
    # Optional filtering
    advise_filter = request.GET.get('advise')
    if advise_filter:
        ipos = ipos.filter(advise=advise_filter)
        
    context = {
        'ipos': ipos,
        'title': 'IPO Management',
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
    }
    return render(request, 'core/ipo.html', context)

def about_project(request):
    """Project Report Page."""
    return render(request, 'core/about_project.html')

@login_required
def dashboard(request):
    target_user, is_family_view, is_consolidated = get_target_user(request)
    recommendations, realized_profits, strategy_stocks = get_recommendations(request.user if is_consolidated else target_user, is_consolidated=is_consolidated)
    
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
    
    total_day_change = sum(r.get('total_day_change', 0) for r in recommendations if r.get('in_portfolio'))
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
        last_updated = timezone.now()

    from .models import PortfolioValueHistory
    history = PortfolioValueHistory.objects.filter(user=request.user).order_by('-date')[:30][::-1]
    history_labels = [h.date.strftime('%d %b') for h in history]
    history_values = [float(h.net_worth) for h in history]
    history_invested = [float(h.invested_value) for h in history]

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
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
        'history_labels': history_labels,
        'history_values': history_values,
        'history_invested': history_invested,
        'news_alerts': NewsAlert.objects.filter(instrument__in=[r.get('instrument_obj') for r in recommendations if r.get('in_portfolio') and r.get('instrument_obj')]).order_by('-news_date', '-created_at')[:10]
    }

    # Record current value history for users
    from .utils import record_portfolio_value_history
    record_portfolio_value_history(request.user)
    
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
@prevent_duplicate_submissions
def add_portfolio_item(request):
    from django.forms import formset_factory
    from .utils import execute_stock_buy, resolve_instrument
    
    StockFormSet = formset_factory(ManualPortfolioForm, extra=1)
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    if request.method == 'POST':
        formset = StockFormSet(request.POST)
        if formset.is_valid():
            success_count = 0
            for form in formset:
                if form.cleaned_data:
                    symbol = form.cleaned_data.get('symbol', '').strip().upper()
                    quantity = form.cleaned_data.get('quantity')
                    avg_cost = form.cleaned_data.get('avg_cost')
                    date = form.cleaned_data.get('date')
                    notes = form.cleaned_data.get('notes')
                    
                    if symbol and quantity and avg_cost and date:
                        inst = resolve_instrument(symbol)
                        if inst:
                            trade_type = form.cleaned_data.get('trade_type', 'NORMAL')
                            execute_stock_buy(target_user, inst, quantity, avg_cost, date, notes, trade_type=trade_type)
                            success_count += 1
            
            if success_count > 0:
                messages.success(request, f"Successfully added {success_count} assets to {target_user.username if is_family_view else 'account'}.")
                url = redirect('dashboard').url
                if is_family_view:
                    url += f"?user_id={target_user.id}"
                return redirect(url)
            else:
                messages.warning(request, "No valid assets were entered.")
    else:
        formset = StockFormSet()
        
    return render(request, 'core/add_portfolio.html', {
        'formset': formset, 
        'title': 'Add Stocks (Bulk)',
        'is_family_view': is_family_view,
        'target_user': target_user
    })

@login_required
@prevent_duplicate_submissions
def sell_portfolio_item(request):
    from django.forms import formset_factory
    from .utils import execute_stock_sell, resolve_instrument
    
    SellFormSet = formset_factory(ManualSellForm, extra=1)
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    if request.method == 'POST':
        formset = SellFormSet(request.POST)
        if formset.is_valid():
            success_count = 0
            for form in formset:
                if form.cleaned_data:
                    symbol = form.cleaned_data.get('symbol', '').strip().upper()
                    quantity = form.cleaned_data.get('quantity')
                    price = form.cleaned_data.get('price')
                    exit_date = form.cleaned_data.get('date') or timezone.localdate()
                    notes = form.cleaned_data.get('notes')
                    sell_type = form.cleaned_data.get('sell_type', 'NORMAL')

                    if symbol and quantity and price:
                        inst = resolve_instrument(symbol)
                        if inst:
                            try:
                                execute_stock_sell(
                                    user=target_user,
                                    instrument=inst,
                                    quantity_to_sell=quantity,
                                    price=price,
                                    exit_date=exit_date,
                                    trade_type=sell_type
                                )
                                success_count += 1
                            except Exception as e:
                                messages.error(request, f"Error selling {symbol}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f"Successfully sold {success_count} assets from {target_user.username if is_family_view else 'account'}.")
                url = redirect('dashboard').url
                if is_family_view:
                    url += f"?user_id={target_user.id}"
                return redirect(url)
            else:
                messages.warning(request, "No valid sales were recorded.")
    else:
        formset = SellFormSet()
        
    return render(request, 'core/sell_portfolio.html', {
        'formset': formset, 
        'title': 'Sell Stocks (Bulk)',
        'is_family_view': is_family_view,
        'target_user': target_user
    })

@login_required
def upload_portfolio(request):
    target_user, is_family_view, is_consolidated = get_target_user(request)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = handle_uploaded_file(request.FILES['file'])
            if df is not None:
                # Strict Header Validation
                uploaded_headers = [h.strip() for h in df.columns]
                required_headers = ['Instrument', 'Quantity', 'Average Cost', 'LTP']
                missing_headers = [h for h in required_headers if h not in uploaded_headers]
                
                if missing_headers:
                    messages.error(request, f"Missing required headers: {missing_headers}. Required: {required_headers}")
                    return redirect('upload_portfolio')

                try:
                    with db_transaction.atomic():
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

                            # Standard Industry Practice: The Average Cost in a portfolio export usually ALREADY includes brokerage.
                            # We will use the provided Average Cost as the direct price for the lot.
                            # If you need to add extra charges, update them manually or via transaction upload.
                            price_with_brokerage = Decimal(str(avg))

                            # Capture Date if provided in CSV
                            raw_date = row.get('Date')
                            if pd.notna(raw_date):
                                try:
                                    tx_date = pd.to_datetime(raw_date).date()
                                except:
                                    tx_date = timezone.localdate()
                            else:
                                tx_date = timezone.localdate()

                            # Create Transaction record for each row (lot preservation)
                            Transaction.objects.create(
                                user=target_user,
                                instrument=inst,
                                transaction_type='BUY',
                                quantity=qty,
                                remaining_quantity=qty,
                                price=price_with_brokerage,
                                date=tx_date
                            )

                            # Aggregate data for Portfolio update
                            if clean_symbol not in aggregated_data:
                                aggregated_data[clean_symbol] = {
                                    'qty': qty,
                                    'total_cost': Decimal(str(qty)) * price_with_brokerage,
                                    'ltp': ltp,
                                    'instrument': inst
                                }
                            else:
                                aggregated_data[clean_symbol]['qty'] += qty
                                aggregated_data[clean_symbol]['total_cost'] += Decimal(str(qty)) * price_with_brokerage
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
                                user=target_user,
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
                except Exception as e:
                    logger.error(f"Portfolio upload failed: {e}")
                    messages.error(request, f"Portfolio upload failed: {type(e).__name__}. No changes were saved.")
                    return redirect('upload_portfolio')

                    messages.success(request, f"Portfolio uploaded successfully for {target_user.username if is_family_view else 'account'}.")
                    url = redirect('dashboard').url
                    if is_family_view:
                        url += f"?user_id={target_user.id}"
                    return redirect(url)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f"Upload failed: {type(e).__name__}: {e}")
            else:
                messages.error(request, "Invalid file format. Please upload a .csv or .xlsx file.")
    else:
        form = UploadFileForm()
    return render(request, 'core/upload.html', {
        'form': form, 
        'title': 'Portfolio',
        'is_family_view': is_family_view,
        'target_user': target_user
    })

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
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = handle_uploaded_file(request.FILES['file'])
            if df is not None:
                uploaded_headers = [h.strip() for h in df.columns]
                expected_headers = TRADE_HEADERS
                
                # Check if uploaded headers match the expected headers (relaxed check: check if all expected are present)
                missing_headers = [h for h in expected_headers if h not in uploaded_headers]
                if missing_headers:
                    messages.error(request, f"Header mismatch. Missing: {missing_headers}. Expected: {expected_headers}")
                    return redirect('upload_pnl')

                # Sorting: Ensure BUYS come before SELLS on the same date for correct FIFO
                try:
                    # Convert 'Trade Date' to datetime for robust sorting
                    df['Trade Date'] = pd.to_datetime(df['Trade Date'], dayfirst=True)
                    # Sort by Date ASC, and then by Trade Type ('BUY' < 'SELL')
                    df = df.sort_values(by=['Trade Date', 'Trade Type'], ascending=[True, True])
                except Exception as e:
                    logger.error(f"Sorting failed in upload_pnl: {e}")
                    # Continue anyway, but sorting is preferred

                count = 0
                instruments_to_sync = set()
                
                try:
                    with db_transaction.atomic():
                        for _, row in df.iterrows():
                            symbol = str(row.get('Symbol')).strip().upper()
                            trade_date = row.get('Trade Date')
                            trade_type = str(row.get('Trade Type')).strip().upper()
                            qty = clean_numeric(row.get('Quantity'), to_int=True)
                            price = clean_numeric(row.get('Price'))
                            
                            if not (symbol and trade_date and trade_type and qty and price):
                                continue
                                
                            from core.utils import resolve_instrument, recalculate_instrument_lots
                            inst = resolve_instrument(symbol)
                            if not inst:
                                messages.warning(request, f"Skipped '{symbol}': Not in verified database.")
                                continue
                                
                            # Date Parsing
                            try:
                                dt = trade_date.date() if hasattr(trade_date, 'date') else pd.to_datetime(trade_date).date()
                            except:
                                continue
                                
                            # Create Transaction
                            Transaction.objects.create(
                                user=target_user, 
                                instrument=inst, 
                                transaction_type=trade_type,
                                quantity=qty, 
                                remaining_quantity=qty if trade_type == 'BUY' else 0, 
                                price=price, 
                                date=dt
                            )
                            instruments_to_sync.add(inst)
                            count += 1
                        
                        # Step 3: Trigger Central Engine for each instrument
                        for inst in instruments_to_sync:
                            recalculate_instrument_lots(target_user, inst)
                            
                except Exception as e:
                    logger.error(f"Upload failed: {e}")
                    messages.error(request, f"Upload failed: {type(e).__name__}. No changes were saved.")
                    return redirect('upload_pnl')
                
                messages.success(request, f"{count} trade records processed for {target_user.username if is_family_view else 'account'}.")
                url = redirect('dashboard').url
                if is_family_view:
                    url += f"?user_id={target_user.id}"
                return redirect(url)
    else:
        form = UploadFileForm()
    
    sample_csv = 'samples/sample_pnl.csv'
    sample_xlsx = 'samples/sample_pnl.xlsx'
    
    return render(request, 'core/upload.html', {
        'form': form, 
        'title': 'P&L Upload (Transactions)',
        'is_family_view': is_family_view,
        'target_user': target_user,
        'sample_csv': sample_csv,
        'sample_xlsx': sample_xlsx
    })

def upload_rpnl(request):
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            df = handle_uploaded_file(request.FILES['file'])
            if df is not None:
                uploaded_headers = [h.strip() for h in df.columns]
                expected_headers = PNL_HEADERS
                
                missing_headers = [h for h in expected_headers if h not in uploaded_headers]
                if missing_headers:
                    messages.error(request, f"Header mismatch. Missing: {missing_headers}. Expected: {expected_headers}")
                    return redirect('upload_rpnl')

                count = 0
                try:
                    with db_transaction.atomic():
                        # Logic for RPNL format (Pre-calculated PnL records)
                        for _, row in df.iterrows():
                            symbol = row.get('Symbol')
                            qty = clean_numeric(row.get('Quantity'), to_int=True)
                            sell_val = clean_numeric(row.get('Sell Value'))
                            buy_val = clean_numeric(row.get('Buy Value'))
                            profit = clean_numeric(row.get('Profit'))
                            entry_date = row.get('Entry Date')
                            exit_date = row.get('Exit Date')
                            
                            if symbol and qty and profit:
                                from core.utils import resolve_instrument
                                inst = resolve_instrument(str(symbol).strip())
                                if not inst:
                                    messages.warning(request, f"Skipped '{symbol}': Not in verified database.")
                                    continue
                                
                                exists = PnLStatement.objects.filter(
                                    user=target_user, instrument=inst, quantity=qty, sell_value=sell_val
                                ).exists()
                                
                                if not exists:
                                    from .utils import execute_stock_sell
                                    try:
                                        # Try to use execute_stock_sell to update holdings and lots
                                        # Calculate a unit price for the sell execution
                                        sell_price = Decimal(str(sell_val)) / Decimal(str(qty)) if qty and sell_val else Decimal('0')
                                        
                                        # Parse exit date
                                        ex_date = None
                                        if exit_date and str(exit_date).lower() != 'nan':
                                            try:
                                                ex_date = pd.to_datetime(exit_date).date()
                                            except:
                                                pass
                                        
                                        # This will consume lots, create a SELL transaction, and record PnL
                                        execute_stock_sell(
                                            target_user, inst, qty, 
                                            sell_price, 
                                            exit_date=ex_date
                                        )
                                        count += 1
                                    except Exception as e:
                                        en_date = pd.to_datetime(entry_date).date() if entry_date and str(entry_date).lower() != 'nan' else None
                                        ex_date = pd.to_datetime(exit_date).date() if exit_date and str(exit_date).lower() != 'nan' else None
                                        
                                        # Create the PnL entry
                                        PnLStatement.objects.create(
                                            user=target_user, instrument=inst, quantity=qty,
                                            buy_value=buy_val or 0, sell_value=sell_val or 0, realized_profit=profit,
                                            entry_date=en_date, exit_date=ex_date
                                        )
                                        
                                        # Create historical transactions so they show up in lot breakdown
                                        if en_date:
                                            b_price = Decimal(str(buy_val)) / Decimal(str(qty)) if qty else 0
                                            Transaction.objects.create(
                                                user=target_user, instrument=inst, transaction_type='BUY',
                                                quantity=qty, remaining_quantity=0, price=b_price, date=en_date
                                            )
                                        if ex_date:
                                            s_price = Decimal(str(sell_val)) / Decimal(str(qty)) if qty else 0
                                            Transaction.objects.create(
                                                user=target_user, instrument=inst, transaction_type='SELL',
                                                quantity=qty, price=s_price, date=ex_date
                                            )
                                        count += 1
                except Exception as e:
                    logger.error(f"RPNL upload failed: {e}")
                    messages.error(request, f"RPNL upload failed: {type(e).__name__}. No changes were saved.")
                    return redirect('upload_rpnl')
                
                messages.success(request, f"{count} realized pnl records processed for {target_user.username if is_family_view else 'account'}.")
                url = redirect('dashboard').url
                if is_family_view:
                    url += f"?user_id={target_user.id}"
                return redirect(url)
    else:
        form = UploadFileForm()
    
    sample_csv = 'samples/sample_rpnl.csv'
    sample_xlsx = 'samples/sample_rpnl.xlsx'
    
    return render(request, 'core/upload.html', {
        'form': form, 
        'title': 'Realized P&L Upload (Settled)',
        'is_family_view': is_family_view,
        'target_user': target_user,
        'sample_csv': sample_csv,
        'sample_xlsx': sample_xlsx
    })

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
    # Cleanup existing SignupOTP for this email (email is encrypted, so we iterate)
    for o in SignupOTP.objects.all():
        if o.email and o.email.lower() == email:
            o.delete()
    SignupOTP.objects.create(email=email, code=code)

    # Send email
    try:
        send_mail(
            subject='Your FOLIUX Registration Code',
            message=(
                f'Your 6-digit verification code is: {code}\n\n'
                f'This code is valid for 10 minutes.\n\n'
                f'If you did not request this, please ignore this email.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
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

    # Lookup SignupOTP by iterating (fields are encrypted, but we filter by time to optimize)
    otp_obj = None
    ten_mins_ago = timezone.now() - timedelta(minutes=10)
    recent_signup_otps = SignupOTP.objects.filter(created_at__gte=ten_mins_ago).order_by('-created_at')
    
    for o in recent_signup_otps:
        if o.email and str(o.email).lower() == str(email) and str(o.code) == str(code):
            otp_obj = o
            break

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
            for o in SignupOTP.objects.all():
                if o.email and o.email.lower() == post_email:
                    o.delete()

            login(request, user, backend='core.backends.EmailOrMobileBackend')

            # Send Welcome Email
            try:
                send_mail(
                    subject='Welcome to FOLIUX',
                    message=f'Hi {user.email},\n\nWelcome to FOLIUX Investment Tracking System. Thank you for registering with us.\n\nBest Regards,\nFOLIUX Team',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, "Registration successful. Welcome email sent.")
            except Exception as e:
                print(f"Error sending email: {e}")
                messages.success(request, "Registration successful, but failed to send welcome email.")

            return redirect('landing')
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
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('edit_profile')
    else:
        form = ProfileForm(instance=profile)
    
    # Get linked family members for display
    from .models import FamilyLink
    linked_family = FamilyLink.objects.filter(user=request.user, is_verified=True).select_related('family_user__profile')
    pending_family = FamilyLink.objects.filter(user=request.user, is_verified=False).select_related('family_user__profile')
    
    # Get hidden signals
    hidden_signals = profile.user.hidden_signals.all().select_related('instrument')
    
    return render(request, 'core/edit_profile.html', {
        'form': form,
        'linked_family': linked_family,
        'pending_family': pending_family,
        'hidden_signals': hidden_signals
    })

@login_required
def link_family_id(request):
    if request.method == 'POST':
        family_id = request.POST.get('family_id', '').strip()
        if not family_id:
            messages.error(request, "Please enter a valid Family ID (Email or Mobile Number).")
            return redirect('edit_profile')
            
        # Try to find user by email or mobile
        from .models import Profile, FamilyLink, OTP
        from django.db.models import Q
        
        target_user = None
        # Check by email/username
        target_user = User.objects.filter(Q(email__iexact=family_id) | Q(username__iexact=family_id)).first()
        
        if not target_user:
            # Check by mobile (mobile_number is encrypted, so we must iterate if it's not a lot of users)
            # Since User count is small, this is acceptable.
            profiles = Profile.objects.exclude(mobile_number__isnull=True).exclude(mobile_number='')
            for p in profiles:
                if p.mobile_number == family_id:
                    target_user = p.user
                    break
                
        if not target_user:
            messages.error(request, f"No user found with Family ID: {family_id}")
            return redirect('edit_profile')
            
        if target_user == request.user:
            messages.error(request, "You cannot link your own account as a family member.")
            return redirect('edit_profile')
            
        # Check if already linked
        existing = FamilyLink.objects.filter(user=request.user, family_user=target_user).first()
        if existing and existing.is_verified:
            messages.info(request, "This account is already linked to your profile.")
            return redirect('dashboard')
            
        # Create unverified link or reuse existing
        if not existing:
            FamilyLink.objects.create(user=request.user, family_user=target_user, is_verified=False)
            
        # Generate OTP for target user
        code = str(random.randint(100000, 999999))
        OTP.objects.filter(user=target_user).delete()
        OTP.objects.create(user=target_user, code=code)
        
        # Send OTP
        try:
            subject = "Family Account Linking Request - FOLIUX"
            requester_name = request.user.profile.full_name or request.user.email
            message = f"User {requester_name} has requested to link your portfolio as a family member. \n\nYour verification code is: {code}\n\nPlease provide this code to them if you wish to authorize the link. This allows them to view and manage your portfolio data separately from theirs."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [target_user.email])
            
            messages.success(request, f"An OTP has been sent to the registered email of {family_id}. Please enter it below.")
            request.session['linking_family_user_id'] = target_user.id
            return redirect('verify_family_otp')
        except Exception as e:
            logger.error(f"Error sending family OTP: {e}")
            messages.error(request, "Failed to send OTP. Please ensure the target user has a valid email.")
            return redirect('edit_profile')

    return redirect('edit_profile')

@login_required
def verify_family_otp(request):
    target_user_id = request.session.get('linking_family_user_id')
    if not target_user_id:
        return redirect('edit_profile')
        
    target_user = get_object_or_404(User, id=target_user_id)
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()
        from .models import OTP, FamilyLink
        
        otp_obj = OTP.objects.filter(user=target_user).order_by('-created_at').first()
        if otp_obj and str(otp_obj.code) == str(otp_code) and otp_obj.is_valid():
            # SUCCESS
            link = FamilyLink.objects.filter(user=request.user, family_user=target_user).first()
            if link:
                link.is_verified = True
                link.save()
                
            # Cleanup
            otp_obj.delete()
            del request.session['linking_family_user_id']
            
            messages.success(request, f"Successfully linked {target_user.username}'s portfolio to your account!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid or expired OTP.")
            
    return render(request, 'core/verify_family_otp.html', {'target_user': target_user})

@login_required
def unlink_family(request, pk):
    from .models import FamilyLink
    link = get_object_or_404(FamilyLink, pk=pk, user=request.user)
    link.delete()
    messages.success(request, "Family account unlinked successfully.")
    return redirect('edit_profile')


@login_required
@csrf_exempt
@prevent_duplicate_submissions
def buy_stock(request):
    if request.method == 'POST':
        target_user, is_family_view, is_consolidated = get_target_user(request)
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
        notes = request.POST.get('notes', '').strip()
        
        transaction_date = pd.to_datetime(date_str).date() if date_str else timezone.localdate()
        if transaction_date > timezone.localdate():
            messages.error(request, "Date cannot be in the future.")
            return redirect('dashboard')
        
        from .utils import execute_stock_buy, resolve_instrument
        try:
            inst = resolve_instrument(symbol)
            if not inst:
                # Fallback for manual addition if not found or not verified
                inst, _ = Instrument.objects.get_or_create(symbol=symbol, defaults={'name': symbol, 'is_verified': True})
            
            trade_type = request.POST.get('trade_type', 'NORMAL')
            execute_stock_buy(target_user, inst, quantity, price, date_str, notes, trade_type=trade_type)
            
            messages.success(request, f"Bought {quantity} units of {symbol} for {target_user.username if is_family_view else 'account'}")
        except Exception as e:
            messages.error(request, str(e))

        url = redirect('dashboard').url
        if is_family_view:
            url += f"?user_id={target_user.id}"
        return redirect(url)
    return redirect('dashboard')

@login_required
@csrf_exempt
@prevent_duplicate_submissions
def sell_stock(request):
    if request.method == 'POST':
        target_user, is_family_view, is_consolidated = get_target_user(request)
        symbol = request.POST.get('symbol', '').strip().upper()
        quantity_to_sell = int(request.POST.get('quantity', 0))
        price = Decimal(request.POST.get('price', '0'))
        exit_date_str = request.POST.get('exit_date')
        
        from .utils import execute_stock_sell
        try:
            inst = get_object_or_404(Instrument, symbol__iexact=symbol, is_verified=True)
            trade_type = request.POST.get('trade_type', 'NORMAL')
            profit, is_intraday_pnl = execute_stock_sell(target_user, inst, quantity_to_sell, price, exit_date_str, trade_type=trade_type)
            
            messages.success(request, f"Sold {quantity_to_sell} units of {symbol} for {target_user.username if is_family_view else 'account'}. Profit: {profit}")
        except Exception as e:
            messages.error(request, str(e))
            
        url = redirect('dashboard').url
        if is_family_view:
            url += f"?user_id={target_user.id}"
        return redirect(url)
    return redirect('dashboard')

@login_required
@csrf_exempt
@prevent_duplicate_submissions
def sell_specific_lot(request):
    if request.method == 'POST':
        target_user, is_family_view, is_consolidated = get_target_user(request)
        lot_id = request.POST.get('lot_id')
        symbol = request.POST.get('symbol', '').strip().upper()
        quantity_to_sell = int(request.POST.get('quantity', 0))
        price = Decimal(request.POST.get('price', '0'))
        exit_date_str = request.POST.get('exit_date')
        
        from .utils import execute_stock_sell
        try:
            inst = get_object_or_404(Instrument, symbol__iexact=symbol, is_verified=True)
            sell_type = request.POST.get('sell_type', 'NORMAL')
            # Pass target_lot_id to execute_stock_sell to bypass FIFO
            profit, is_intraday_pnl = execute_stock_sell(
                target_user, 
                inst, 
                quantity_to_sell, 
                price, 
                exit_date_str, 
                target_lot_id=lot_id,
                trade_type=sell_type
            )
            
            messages.success(request, f"Sold {quantity_to_sell} units of {symbol} from specific lot. Profit: {profit}")
        except Exception as e:
            messages.error(request, str(e))
            
        return redirect('lot_breakdown', instrument_id=inst.id)
    return redirect('dashboard')
def get_current_financial_year():
    now = timezone.localdate()
    # Standard Indian Financial Year starts April 1.
    # User requested transition to 2026-2027 starting March 27, 2026.
    if now.month >= 4 or (now.year == 2026 and now.month == 3 and now.day >= 27):
        return f"{now.year}-{now.year+1}"
    else:
        return f"{now.year-1}-{now.year}"

@login_required
def transaction_history(request):
    """View all buy/sell transactions for the user."""
    target_user, is_family_view, is_consolidated = get_target_user(request)
    transactions = Transaction.objects.filter(user=target_user).select_related('instrument').order_by('-date', '-created_at')
    
    current_fy_str = get_current_financial_year()
    portfolios = Portfolio.objects.filter(user=target_user)
    current_invested = sum(p.invested_amount for p in portfolios)
    current_value = sum(p.current_value for p in portfolios)
    current_unrealized = sum(p.unrealized_pnl for p in portfolios)
    
    start_year = int(current_fy_str.split('-')[0])
    end_year = int(current_fy_str.split('-')[1])
    
    total_realized_profits = PnLStatement.objects.filter(user=target_user)
    total_realized = sum(rp.realized_profit for rp in total_realized_profits)
    
    past_fys = FinancialYearData.objects.filter(user=target_user).exclude(financial_year=current_fy_str)
    past_fys_realized_sum = sum(fd.realized_profit for fd in past_fys)
    
    current_realized = total_realized - past_fys_realized_sum
    
    # Automatically add/update current FY
    current_fy_obj, _ = FinancialYearData.objects.update_or_create(
        user=target_user,
        financial_year=current_fy_str,
        defaults={
            'invested_amount': current_invested,
            'current_value': current_value,
            'unrealized_pnl': current_unrealized,
            'realized_profit': current_realized
        }
    )
    
    # Get all FY data (including current that we just saved/updated) ordered by most recent
    fy_data = FinancialYearData.objects.filter(user=target_user).order_by('-financial_year')
    current_fy_data = [fd for fd in fy_data if fd.financial_year == current_fy_str]
    past_fy_data = [fd for fd in fy_data if fd.financial_year != current_fy_str]
    
    # Record current value history
    from .utils import record_portfolio_value_history
    record_portfolio_value_history(target_user)

    # Get Portfolio Performance History (Since Inception or at least 180 days)
    first_tx = Transaction.objects.filter(user=target_user).order_by('date').first()
    
    if first_tx:
        # Show history since the first transaction
        history = PortfolioValueHistory.objects.filter(user=target_user, date__gte=first_tx.date).order_by('date')
    else:
        # Fallback to last 180 days
        history = PortfolioValueHistory.objects.filter(user=target_user, date__gte=timezone.localdate() - timedelta(days=180)).order_by('date')
    
    # Calculate NIFTY Scaling Ratio based on first ever record
    first_history = PortfolioValueHistory.objects.filter(user=target_user).order_by('date').first()
    base_nifty = float(first_history.nifty_price) if (first_history and first_history.nifty_price) else 1.0
    base_current = float(first_history.stock_current) if (first_history and first_history.stock_current) else 1.0
    # Avoid zero ratio
    ratio = base_current / base_nifty if base_nifty > 0 else 1.0

    history_data = {
        'dates': [h.date.strftime('%b %d, %Y') for h in history],
        'invested': [float(h.stock_invested) for h in history],
        'current': [float(h.stock_current) for h in history],
        'net_worth': [float(h.stock_current) for h in history],
        'nifty': [float(h.nifty_price) if h.nifty_price else None for h in history],
        'nifty_scaled': [round(float(h.nifty_price) * ratio, 2) if h.nifty_price else None for h in history]
    }
    
    return render(request, 'core/transactions.html', {
        'transactions': transactions,
        'current_fy_data': current_fy_data[0] if current_fy_data else None,
        'past_fy_data': past_fy_data,
        'history_data_json': json.dumps(history_data),
        'portfolio_history': history.order_by('-date'),
        'target_user': target_user,
        'is_family_view': is_family_view
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
        from decimal import Decimal
        try:
            data = json.loads(request.body)
            fy = data.get('year')
            from .models import FinancialYearData
            obj = get_object_or_404(FinancialYearData, user=request.user, financial_year=fy)
            
            # If data is provided, save it before toggling (only if currently unlocked)
            if not obj.is_locked:
                invested = data.get('invested')
                current = data.get('current')
                unrealized = data.get('unrealized')
                realized = data.get('realized')
                
                if invested is not None: obj.invested_amount = Decimal(str(invested))
                if current is not None: obj.current_value = Decimal(str(current))
                if unrealized is not None: obj.unrealized_pnl = Decimal(str(unrealized))
                if realized is not None: obj.realized_profit = Decimal(str(realized))
            
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
    target_user, is_family_view, is_consolidated = get_target_user(request)
    if is_consolidated:
        from .utils import get_consolidated_users
        user_ids = get_consolidated_users(request.user)
        lots = Transaction.objects.filter(
            user_id__in=user_ids,
            instrument=inst,
            transaction_type='BUY'
        ).order_by('date', 'created_at').select_related('user__profile')
    else:
        lots = Transaction.objects.filter(
            user=target_user,
            instrument=inst,
            transaction_type='BUY'
        ).order_by('date', 'created_at').select_related('user__profile')
    
    # Enrich lots with days held and unrealized P&L
    live_ltps = fetch_live_ltp()
    ltp = Decimal(str(live_ltps.get(inst.symbol.upper(), 0)))
    
    # Fallback: if live LTP is 0, try Instrument.last_price, then Portfolio stored ltp
    if not ltp or ltp <= 0:
        ltp = inst.last_price or Decimal('0')
    if not ltp or ltp <= 0:
        portfolio = Portfolio.objects.filter(user=target_user, instrument=inst).first()
        if portfolio:
            ltp = portfolio.ltp or Decimal('0')
    
    # --- Build unified timeline: BUY lots + SELL records ---
    unified_records = []
    
    # Summary stats for BUY (only for active holdings)
    total_quantity = 0
    total_invested = Decimal('0')
    total_unrealized_pnl = Decimal('0')
    
    # Fetch SELL records from PnLStatement
    if is_consolidated:
        sell_records = PnLStatement.objects.filter(
            user_id__in=user_ids,
            instrument=inst,
        ).order_by('-exit_date').select_related('user__profile')
    else:
        sell_records = PnLStatement.objects.filter(
            user=target_user,
            instrument=inst,
        ).order_by('-exit_date').select_related('user__profile')
    
    # Map entry_date to exit_date for sold lot period calculation
    entry_to_exit_map = {sr.entry_date: sr.exit_date for sr in sell_records if sr.entry_date}

    # Add active and historical BUY lots
    for lot in lots:
        # For active lots, calculate P&L
        if lot.remaining_quantity > 0:
            days_held = (timezone.localdate() - lot.date).days
            current_value = Decimal(str(lot.remaining_quantity)) * ltp
            buy_value = Decimal(str(lot.remaining_quantity)) * lot.price
            pnl = current_value - buy_value
            pnl_pct = (pnl / buy_value * 100) if buy_value else 0
            
            total_quantity += lot.remaining_quantity
            total_invested += buy_value
            total_unrealized_pnl += pnl
        else:
            # For sold lots, try to find the exit date from matched PnL
            exit_date = entry_to_exit_map.get(lot.date)
            if exit_date:
                days_held = (exit_date - lot.date).days
            else:
                days_held = None
            pnl = None
            pnl_pct = None

        unified_records.append({
            'type': 'BUY',
            'id': lot.id,
            'owner': lot.user.profile.full_name or lot.user.username,
            'sort_date': lot.date,
            'date': lot.date,
            'quantity': lot.quantity, # Show original quantity in history
            'remaining_quantity': lot.remaining_quantity,
            'price': lot.price,
            'trade_type': lot.trade_type,
            'days_held': days_held,
            'ltp': ltp,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
        })
    
    # Summary stats for BUY
    total_unrealized_pnl_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
    avg_cost = total_invested / Decimal(str(total_quantity)) if total_quantity > 0 else 0
    
    
    # Fetch SELL records from PnLStatement
    if is_consolidated:
        sell_records = PnLStatement.objects.filter(
            user_id__in=user_ids,
            instrument=inst,
        ).order_by('-exit_date').select_related('user__profile')
    else:
        sell_records = PnLStatement.objects.filter(
            user=target_user,
            instrument=inst,
        ).order_by('-exit_date').select_related('user__profile')

    total_sell_quantity = 0
    total_realized_pnl = Decimal('0')
    total_pnl_buy_val = Decimal('0')
    first_sell_date = None

    for sr in sell_records:
        if first_sell_date is None or sr.exit_date < first_sell_date:
            first_sell_date = sr.exit_date
            
        holding_days = (sr.exit_date - sr.entry_date).days if sr.entry_date else None
        pnl_pct = (sr.realized_profit / sr.buy_value * 100) if sr.buy_value else 0
        sell_price = sr.sell_value / Decimal(str(sr.quantity)) if sr.quantity else Decimal('0')
        buy_price = sr.buy_value / Decimal(str(sr.quantity)) if sr.quantity else Decimal('0')
        
        unified_records.append({
            'type': 'SELL',
            'id': sr.id,
            'owner': sr.user.profile.full_name or sr.user.username,
            'sort_date': sr.exit_date,
            'date': sr.exit_date,
            'entry_date': sr.entry_date,
            'quantity': sr.quantity,
            'price': sell_price,
            'buy_price': buy_price,
            'pnl': sr.realized_profit,
            'pnl_pct': pnl_pct,
            'holding_days': holding_days,
            'trade_type': sr.trade_type,
            'is_intraday': (sr.entry_date == sr.exit_date) if sr.entry_date else False
        })
        total_sell_quantity += sr.quantity
        total_realized_pnl += sr.realized_profit
        total_pnl_buy_val += sr.buy_value
    
    # Sort unified list by date descending (newest first)
    unified_records.sort(key=lambda r: (r['sort_date'], 0 if r['type'] == 'BUY' else 1), reverse=True)
    
    context = {
        'instrument': inst,
        'records': unified_records,
        'ltp': ltp,
        'total_quantity': total_quantity,
        'total_invested': total_invested,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_unrealized_pnl_pct': total_unrealized_pnl_pct,
        'avg_cost': avg_cost,
        'total_sell_quantity': total_sell_quantity,
        'total_realized_pnl': total_realized_pnl,
        'is_consolidated': is_consolidated,
        'is_family_view': is_family_view,
        'target_user': target_user,
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
    
    # Rate limit: 10 minutes (600 seconds)
    last_sync = cache.get(sync_key)
    now = timezone.now().timestamp()
    
    if last_sync is not None and (now - last_sync) < 600:
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
            # Use fast_info for real-time accuracy, fallback to history
            try:
                prev_price = float(ticker.fast_info['previous_close'])
            except:
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
            elif 'BZ=F' in symbol: name = 'Brent Crude'
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
            # Use fast_info for real-time accuracy, fallback to history
            try:
                prev_price = float(ticker.fast_info['previous_close'])
            except:
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
    from decimal import Decimal
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)
    
    # If query is a numeric scheme code, fetch and return NAV immediately
    if query.isdigit():
        fund = MutualFund.objects.filter(scheme_code=query).first()
        if not fund:
            fund = MutualFund.objects.filter(symbol=query).first()
        if fund and fund.nav > 0:
            return JsonResponse([{
                'name': fund.name,
                'symbol': fund.symbol or fund.scheme_code,
                'nav': float(fund.nav)
            }], safe=False)
        else:
            # Fetch from mfapi.in
            from .mf_utils import get_mf_details
            details = get_mf_details(query)
            if details and details.get('data'):
                nav = float(details['data'][0]['nav'])
                name = details.get('meta', {}).get('scheme_name', f"MF {query}")
                amc = details.get('meta', {}).get('fund_house')
                # Save/Update in DB
                fund, _ = MutualFund.objects.update_or_create(
                    scheme_code=query,
                    defaults={'name': name, 'symbol': query, 'nav': Decimal(str(nav)), 'amc': amc}
                )
                return JsonResponse([{
                    'name': fund.name,
                    'symbol': fund.scheme_code,
                    'nav': float(fund.nav)
                }], safe=False)

    # Search specifically in MutualFund model (populated from Excel)
    funds = MutualFund.objects.filter(
        Q(name__icontains=query) | Q(symbol__icontains=query)
    )[:15]
    
    results = []
    seen_symbols = set()
    for f in funds:
        sym = f.symbol or f.scheme_code
        if sym:
            seen_symbols.add(sym.upper())
        results.append({
            'name': f.name,
            'symbol': f.symbol or f.scheme_code,
            'nav': float(f.nav) if f.nav else 0
        })
        
    # Search locally in MutualFundScheme model
    try:
        from core.models import MutualFundScheme
        local_schemes = MutualFundScheme.objects.filter(
            Q(scheme_name__icontains=query) | Q(scheme_code__icontains=query)
        )[:15]
        for item in local_schemes:
            code = str(item.scheme_code)
            if code.upper() not in seen_symbols:
                seen_symbols.add(code.upper())
                results.append({
                    'name': item.scheme_name,
                    'symbol': code,
                    'nav': 0.0
                })
    except Exception as e:
        logger.error(f"Error querying local MutualFundScheme: {e}")
        
    return JsonResponse(results[:15], safe=False)

@csrf_exempt
def coin_price_api(request):
    """API to fetch live price for a coin from the database or yfinance."""
    symbol = request.GET.get('symbol', '').strip().upper()
    if not symbol:
        return JsonResponse({'status': 'error', 'message': 'Symbol required'}, status=400)
    
    # Try a few variations
    coin = Coin.objects.filter(symbol__iexact=symbol).first()
    if not coin and '-' not in symbol:
        coin = Coin.objects.filter(symbol__iexact=f"{symbol}-INR").first()
    
    if not coin:
        # Fallback to yfinance
        try:
            import yfinance as yf
            from decimal import Decimal
            ticker_symbol = symbol
            if '-' not in ticker_symbol and not ticker_symbol.endswith('.NS') and not ticker_symbol.endswith('.BO'):
                ticker_symbol = f"{ticker_symbol}-INR"
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            price_val = info.get('regularMarketPrice') or info.get('previousClose') or info.get('navPrice')
            if price_val:
                name_val = info.get('longName') or info.get('shortName') or symbol.split('-')[0]
                prev_price_val = info.get('previousClose')
                
                defaults = {
                    'name': name_val,
                    'price': Decimal(str(price_val))
                }
                if prev_price_val:
                    defaults['prev_price'] = Decimal(str(prev_price_val))
                
                coin, _ = Coin.objects.update_or_create(
                    symbol=ticker_symbol,
                    defaults=defaults
                )
        except Exception as e:
            logger.error(f"Error fetching coin price from yfinance for {symbol}: {e}")
            
    if not coin:
        # Try spreadsheet sync as a second fallback
        try:
            from .utils import sync_coins_from_sheet
            sync_coins_from_sheet()
            coin = Coin.objects.filter(symbol__iexact=symbol).first()
            if not coin and '-' not in symbol:
                coin = Coin.objects.filter(symbol__iexact=f"{symbol}-INR").first()
        except Exception as e:
            logger.error(f"Spreadsheet sync error: {e}")
    
    if coin:
        return JsonResponse({
            'status': 'success',
            'symbol': coin.symbol,
            'name': coin.name,
            'price': float(coin.price)
        })
    else:
        return JsonResponse({'status': 'error', 'message': 'Price not found in database, spreadsheet or yfinance'}, status=404)

@csrf_exempt
def coin_suggestions_api(request):
    """Provide real-time suggestions based on coin symbol or name from our DB and external API."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'status': 'success', 'results': []})

    from core.models import Coin
    
    # Search locally first
    local_coins = Coin.objects.filter(
        models.Q(symbol__icontains=q) | models.Q(name__icontains=q)
    )
    
    results_map = {}
    for c in local_coins:
        sym = c.symbol.split('-')[0].upper() # extract BTC from BTC-INR
        results_map[sym] = {
            'symbol': c.symbol,
            'name': c.name,
            'price': float(c.price) if c.price else 0.0
        }
        
    # Also fetch from coingecko search
    try:
        import requests
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(f"https://api.coingecko.com/api/v3/search?query={q}", headers=headers, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            for coin in data.get('coins', [])[:10]:
                sym = coin['symbol'].upper()
                if sym not in results_map:
                    results_map[sym] = {
                        'symbol': f"{sym}-INR",
                        'name': coin['name'],
                        'price': 0.0
                    }
    except Exception as e:
        logger.error(f"Error fetching from Coingecko: {e}")
        
    # If the user's exact typed query is not in the map, add it as a fallback option
    q_upper = q.upper()
    if q_upper not in results_map:
        results_map[q_upper] = {
            'symbol': f"{q_upper}-INR",
            'name': q_upper,
            'price': 0.0
        }

    return JsonResponse({'status': 'success', 'results': list(results_map.values())[:15]})

@csrf_exempt
def nps_suggestions_api(request):
    """API for NPS Fund autocomplete by name or code."""
    from django.db.models import Q
    from django.core.cache import cache
    from decimal import Decimal
    from core.models import NPSFund
    import requests
    
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)
        
    # If query is a scheme code (starts with SM), fetch details and return NAV immediately
    if query.upper().startswith('SM') and len(query) >= 6:
        fund = NPSFund.objects.filter(scheme_code__iexact=query).first()
        if not fund:
            fund = NPSFund.objects.filter(name__iexact=query).first()
        if fund and fund.nav > 0:
            return JsonResponse([{
                'name': fund.name,
                'symbol': fund.scheme_code or query.upper(),
                'nav': float(fund.nav)
            }], safe=False)
        else:
            # Fetch from npsnav.in
            url = f"https://npsnav.in/api/detailed/{query.upper()}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    nav_val = float(data.get('NAV', '0'))
                    name_val = data.get('Scheme Name', f"NPS {query.upper()}")
                    # Save/Update in DB
                    fund, _ = NPSFund.objects.update_or_create(
                        scheme_code=query.upper(),
                        defaults={'name': name_val, 'nav': Decimal(str(nav_val))}
                    )
                    return JsonResponse([{
                        'name': fund.name,
                        'symbol': fund.scheme_code,
                        'nav': float(fund.nav)
                    }], safe=False)
            except Exception as e:
                logger.error(f"Error fetching NPS details for {query}: {e}")
                
    # Search locally first
    local_funds = NPSFund.objects.filter(
        Q(name__icontains=query) | Q(scheme_code__icontains=query)
    )[:15]
    
    results = []
    seen_codes = set()
    for f in local_funds:
        code = f.scheme_code or f.name
        seen_codes.add(code.upper())
        results.append({
            'name': f.name,
            'symbol': f.scheme_code or '',
            'nav': float(f.nav) if f.nav else 0.0
        })
        
    # Query npsnav.in schemes list (cached for 24h)
    cache_key = "npsnav_schemes"
    schemes_list = cache.get(cache_key)
    if not schemes_list:
        try:
            url = "https://npsnav.in/api/schemes"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                schemes_list = data.get('data', [])
                cache.set(cache_key, schemes_list, 86400) # cache for 1 day
        except Exception as e:
            logger.error(f"Error fetching NPS schemes list: {e}")
            
    if schemes_list:
        query_lower = query.lower()
        for item in schemes_list:
            code = item[0]
            name = item[1]
            if query_lower in name.lower() or query_lower in code.lower():
                if code.upper() not in seen_codes:
                    seen_codes.add(code.upper())
                    results.append({
                        'name': name,
                        'symbol': code,
                        'nav': 0.0 # Will be fetched dynamically when selected
                    })
                    if len(results) >= 15:
                        break
                        
    return JsonResponse(results[:15], safe=False)

@login_required
def nps_dashboard(request):
    """NPS Portfolio dashboard with active NAV sync."""
    # Trigger auto update if data is stale in background thread
    import threading
    def _run_bg_nps():
        try:
            _auto_update_nps()
        except Exception:
            pass
    threading.Thread(target=_run_bg_nps, daemon=True).start()
    target_user, is_family_view, is_consolidated = get_target_user(request)
    if is_consolidated:
        from .utils import get_consolidated_users
        user_ids = get_consolidated_users(request.user)
        all_holdings_qs = NPSPortfolio.objects.filter(user_id__in=user_ids).select_related('fund')
        
        # Aggregate by fund
        agg_map = {}
        for h in all_holdings_qs:
            fid = h.fund_id
            if fid not in agg_map:
                agg_map[fid] = {
                    'fund': h.fund,
                    'units': Decimal('0'),
                    'invested_amount': Decimal('0'),
                    'realized_profit': Decimal('0'),
                }
            agg_map[fid]['units'] += h.units
            agg_map[fid]['invested_amount'] += h.invested_amount
            agg_map[fid]['realized_profit'] += h.realized_profit
            
        nps_holdings = []
        class MockNPSPortfolio:
            def __init__(self, data):
                self.fund = data['fund']
                self.fund_id = data['fund'].id
                self.units = data['units']
                self.invested_amount = data['invested_amount']
                self.realized_profit = data['realized_profit']
                self.avg_nav = self.invested_amount / self.units if self.units > 0 else 0
            @property
            def current_value(self): return self.units * self.fund.nav
            @property
            def unrealized_pnl(self): return self.current_value - self.invested_amount
            @property
            def pnl_percentage(self): return (self.unrealized_pnl / self.invested_amount * 100) if self.invested_amount > 0 else 0
            @property
            def day_change(self):
                if self.fund.prev_nav == 0: return 0
                return self.units * (self.fund.nav - self.fund.prev_nav)

        for fid, data in agg_map.items():
            if data['units'] > 0:
                nps_holdings.append(MockNPSPortfolio(data))
                
        total_realized_profit = sum(data['realized_profit'] for data in agg_map.values())
    else:
        all_holdings = NPSPortfolio.objects.filter(user=target_user).select_related('fund')
        nps_holdings = [h for h in all_holdings if h.units > 0]
        total_realized_profit = NPSPortfolio.objects.filter(user=target_user).aggregate(
            total=models.Sum('realized_profit'))['total'] or 0

    total_invested = sum(h.invested_amount for h in nps_holdings)
    total_current_value = sum(h.current_value for h in nps_holdings)
    total_unrealized_pnl = sum(h.unrealized_pnl for h in nps_holdings)
    total_day_change = sum(h.day_change for h in nps_holdings)
    
    context = {
        'nps_holdings': nps_holdings,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_day_change': total_day_change,
        'total_realized_profit': total_realized_profit,
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
    }
    return render(request, 'core/nps_dashboard.html', context)

@login_required
def nps_detail(request, pk):
    """View details and performance graph for an NPS fund."""
    fund = get_object_or_404(NPSFund, pk=pk)
    
    # Heuristic for scheme_code if missing
    if not fund.scheme_code:
        # We might need a lookup table or search logic.
        # For now, we'll try to find it by name from a list or just inform user.
        # Actually, let's just use the npsnav.in API if we can find it.
        pass

    history = fund.get_nav_history()
    
    # Prepare data for Chart.js
    chart_data = {
        'labels': [h['date'] for h in history],
        'navs': [float(h['nav']) for h in history]
    }
    
    context = {
        'fund': fund,
        'chart_data': json.dumps(chart_data),
        'latest_nav': history[-1] if history else None,
    }
    return render(request, 'core/nps_detail.html', context)


@login_required
@prevent_duplicate_submissions
def add_nps(request):
    target_user, is_family_view, is_consolidated = get_target_user(request)
    if request.method == 'POST':
        fund_name = request.POST.get('fund_name').strip()
        units = Decimal(request.POST.get('units', '0'))
        avg_nav = Decimal(request.POST.get('avg_nav', '0'))
        date_str = request.POST.get('date')
        transaction_date = pd.to_datetime(date_str).date() if date_str else timezone.localdate()
        if transaction_date > timezone.localdate():
            messages.error(request, "Date cannot be in the future.")
            return redirect('nps_dashboard')
        fund, _ = NPSFund.objects.get_or_create(name=fund_name)
        NPSTransaction.objects.create(
            user=target_user, fund=fund, transaction_type='BUY',
            units=units, remaining_units=units, price=avg_nav, date=transaction_date
        )
        holding, created = NPSPortfolio.objects.get_or_create(
            user=target_user, fund=fund, defaults={'units': 0, 'avg_nav': 0}
        )
        total_units = holding.units + units
        total_cost = (holding.units * holding.avg_nav) + (units * avg_nav)
        holding.units = total_units
        holding.avg_nav = total_cost / total_units if total_units > 0 else 0
        holding.save()
        messages.success(request, f"Added {units} units of {fund_name} for {target_user.username if is_family_view else 'account'}.")
        url = redirect('nps_dashboard').url
        if is_family_view:
            url += f"?user_id={target_user.id}"
        return redirect(url)
    all_funds = NPSFund.objects.all().order_by('name')
    return render(request, 'core/nps_add_item.html', {
        'all_funds': all_funds,
        'is_family_view': is_family_view,
        'target_user': target_user
    })

@login_required
@prevent_duplicate_submissions
def sell_nps(request, pk):
    target_user, is_family_view, is_consolidated = get_target_user(request)
    holding = get_object_or_404(NPSPortfolio, pk=pk, user=target_user)
    if request.method == 'POST':
        units_to_sell = Decimal(request.POST.get('units', '0'))
        sell_price = Decimal(request.POST.get('price', '0'))
        date_str = request.POST.get('date')
        sell_date = pd.to_datetime(date_str).date() if date_str else timezone.localdate()
        if sell_date > timezone.localdate():
            messages.error(request, "Date cannot be in the future.")
            return redirect('nps_dashboard')
        if units_to_sell > holding.units:
            messages.error(request, f"Insufficient units.")
            return redirect('nps_dashboard')
        buy_lots = NPSTransaction.objects.filter(
            user=target_user, fund=holding.fund, transaction_type='BUY', remaining_units__gt=0
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
            user=target_user, fund=holding.fund, transaction_type='SELL',
            units=units_to_sell, price=sell_price, date=sell_date
        )
        holding.units -= units_to_sell
        holding.realized_profit += realized_profit
        remaining_lots = NPSTransaction.objects.filter(
            user=target_user, fund=holding.fund, transaction_type='BUY', remaining_units__gt=0
        )
        total_rem_units = sum(l.remaining_units for l in remaining_lots)
        total_rem_cost = sum(l.remaining_units * l.price for l in remaining_lots)
        if total_rem_units > 0:
            holding.avg_nav = total_rem_cost / total_rem_units
        holding.save()
        messages.success(request, f"Sold {units_to_sell} units for {target_user.username if is_family_view else 'account'}. Profit: ₹{realized_profit:.2f}")
        url = redirect('nps_dashboard').url
        if is_family_view:
            url += f"?user_id={target_user.id}"
        return redirect(url)
    return render(request, 'core/nps_sell_item.html', {
        'holding': holding, 
        'now': timezone.now(),
        'is_family_view': is_family_view,
        'target_user': target_user
    })

@login_required
def delete_nps_portfolio(request, pk):
    target_user, is_family_view, is_consolidated = get_target_user(request)
    holding = get_object_or_404(NPSPortfolio, pk=pk, user=target_user)
    if request.method == 'POST':
        name = holding.fund.name
        holding.delete()
        messages.success(request, f"Removed {name} from {target_user.username if is_family_view else 'account'}.")
    
    url = redirect('nps_dashboard').url
    if is_family_view:
        url += f"?user_id={target_user.id}"
    return redirect(url)

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

def _process_auto_rd_deposits(user):
    """Automatically record RD deposits that have passed since the last execution."""
    from .models import FixedAsset
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal
    from datetime import date
    from django.utils import timezone
    
    today = timezone.localdate()
    active_rds = FixedAsset.objects.filter(user=user, asset_type='RD', next_deposit_date__lte=today)
    
    for rd in active_rds:
        # Limit iterations
        iterations = 0
        while rd.next_deposit_date and today >= rd.next_deposit_date and iterations < 120:
            iterations += 1
            
            # Increase invested amount
            rd.invested_amount = str(rd.invested_amount_decimal + (rd.monthly_deposit or Decimal('0')))
            
            # Update next deposit date
            rd.next_deposit_date = rd.next_deposit_date + relativedelta(months=1)
            
            # Check for maturity
            if rd.maturity_date and rd.next_deposit_date > rd.maturity_date:
                rd.next_deposit_date = None
                break
        rd.save()

@login_required
def fd_dashboard(request):
    """Dashboard for Fixed Assets (FD, RD, PPF, etc) with automation."""
    target_user, is_family_view, is_consolidated = get_target_user(request)
    _process_auto_rd_deposits(target_user)
    
    if is_consolidated:
        from .utils import get_consolidated_users
        user_ids = get_consolidated_users(request.user)
        fd_holdings = FixedAsset.objects.filter(user_id__in=user_ids).order_by('-investment_date')
    else:
        fd_holdings = FixedAsset.objects.filter(user=target_user).order_by('-investment_date')
    
    total_invested = sum(h.invested_amount_decimal for h in fd_holdings)
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
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
    }
    return render(request, 'core/fd_dashboard.html', context)

@login_required
@prevent_duplicate_submissions
def add_fd(request):
    """Add a fixed asset manually."""
    target_user, is_family_view, is_consolidated = get_target_user(request)
    renewal_id = request.GET.get('renewal_id')
    prefill_data = {}
    if renewal_id:
        try:
            old_asset = FixedAsset.objects.get(id=renewal_id, user=target_user)
            prefill_data = {
                'instrument_name': old_asset.instrument_name,
                'asset_type': old_asset.asset_type,
                'invested_amount': old_asset.invested_amount_decimal,
                'interest_rate': old_asset.interest_rate_decimal,
                'monthly_deposit': old_asset.monthly_deposit,
                'tenure_years': old_asset.tenure_years,
                'holder_name': old_asset.holder_name,
                'fd_id': old_asset.fd_id,
            }
        except FixedAsset.DoesNotExist:
            pass

    if request.method == 'POST':
        instrument_name = request.POST.get('instrument_name', '').strip()
        investment_date_str = request.POST.get('investment_date')
        maturity_date_str = request.POST.get('maturity_date')
        holder_name = request.POST.get('holder_name', '').strip()
        fd_id = request.POST.get('fd_id', '').strip()
        
        try:
            invested_amount = Decimal(request.POST.get('invested_amount', '0'))
            interest_rate = Decimal(request.POST.get('interest_rate', '0'))
            investment_date = pd.to_datetime(investment_date_str).date() if investment_date_str else timezone.localdate()
            if investment_date > timezone.localdate():
                messages.error(request, "Investment date cannot be in the future.")
                return redirect('add_fd')
            maturity_date = pd.to_datetime(maturity_date_str).date() if maturity_date_str else None
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid numeric or date values provided.")
            return redirect('add_fd')

        if not instrument_name or invested_amount <= 0 or interest_rate <= 0:
            messages.error(request, "Please provide valid instrument name, amount, and rate.")
            return redirect('add_fd')
            
        asset_type = request.POST.get('asset_type', 'FD')
        monthly_deposit = Decimal(request.POST.get('monthly_deposit', '0') or '0')
        tenure_years = int(request.POST.get('tenure_years', '0') or '0')
        
        if asset_type == 'RD':
            # For RD, invested_amount starts with 1st deposit
            invested_amount = monthly_deposit
            # Calculate maturity date based on tenure
            if tenure_years > 0:
                from dateutil.relativedelta import relativedelta
                maturity_date = investment_date + relativedelta(years=tenure_years)
            
            # Set next deposit date to 1 month from now
            from dateutil.relativedelta import relativedelta
            next_deposit_date = investment_date + relativedelta(months=1)
        else:
            next_deposit_date = None

        FixedAsset.objects.create(
            user=target_user,
            instrument_name=instrument_name,
            asset_type=asset_type,
            invested_amount=str(invested_amount),
            interest_rate=str(interest_rate),
            investment_date=investment_date,
            maturity_date=maturity_date,
            monthly_deposit=monthly_deposit,
            tenure_years=tenure_years,
            next_deposit_date=next_deposit_date,
            holder_name=holder_name,
            fd_id=fd_id,
            parent_asset_id=renewal_id if renewal_id else None
        )
        messages.success(request, f"Added {asset_type}: {instrument_name} for {target_user.username if is_family_view else 'account'}.")
        url = redirect('fd_dashboard').url
        if is_family_view:
            url += f"?user_id={target_user.id}"
        return redirect(url)
        
    return render(request, 'core/fd_add_item.html', {
        'prefill': prefill_data,
        'is_family_view': is_family_view,
        'target_user': target_user
    })

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
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    if is_consolidated:
        from .utils import get_consolidated_users
        user_ids = get_consolidated_users(request.user)
        other_holdings = OtherAsset.objects.filter(user_id__in=user_ids).order_by('-purchase_date')
    else:
        other_holdings = OtherAsset.objects.filter(user=target_user).order_by('-purchase_date')
    
    total_invested = sum(h.purchase_price for h in other_holdings)
    total_current_value = sum(h.current_value for h in other_holdings)
    total_unrealized_pnl = sum(h.unrealized_pnl for h in other_holdings)
    total_monthly_rent = sum((h.monthly_rent or Decimal('0')) for h in other_holdings)
    
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
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
        'last_updated': timezone.now(),
    }
    return render(request, 'core/other_assets_dashboard.html', context)

@login_required
@prevent_duplicate_submissions
def add_other_asset(request):
    """Add a new other asset."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        asset_type = request.POST.get('asset_type', 'Other')
        purchase_date_str = request.POST.get('purchase_date')
        
        try:
            purchase_price = Decimal(request.POST.get('purchase_price', '0'))
            
            # expected_appreciation
            expected_appreciation_str = request.POST.get('expected_appreciation', '0').strip()
            expected_appreciation = Decimal(expected_appreciation_str) if expected_appreciation_str else Decimal('0.00')
            
            # actual_market_value (optional override)
            actual_market_value_str = request.POST.get('actual_market_value', '').strip()
            actual_market_value = Decimal(actual_market_value_str) if actual_market_value_str else None
            
            monthly_rent = Decimal(request.POST.get('monthly_rent', '0'))
            purchase_date = pd.to_datetime(purchase_date_str).date() if purchase_date_str else timezone.localdate()
            if purchase_date > timezone.localdate():
                messages.error(request, "Purchase date cannot be in the future.")
                return redirect('add_other_asset')
            holder_name = request.POST.get('holder_name', '').strip()
            asset_id = request.POST.get('asset_id', '').strip()
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
            expected_appreciation=expected_appreciation,
            actual_market_value=actual_market_value,
            monthly_rent=monthly_rent,
            holder_name=holder_name,
            asset_id=asset_id
        )
        messages.success(request, f"Added Asset: {name}.")
        return redirect('other_assets_dashboard')
        
    return render(request, 'core/other_asset_form.html', {'action': 'Add', 'asset_types': OtherAsset.ASSET_TYPES})

@login_required
@prevent_duplicate_submissions
def edit_other_asset(request, pk):
    """Edit an existing other asset."""
    asset = get_object_or_404(OtherAsset, pk=pk, user=request.user)
    
    if request.method == 'POST':
        asset.name = request.POST.get('name', asset.name).strip()
        asset.asset_type = request.POST.get('asset_type', asset.asset_type)
        purchase_date_str = request.POST.get('purchase_date')
        
        try:
            asset.purchase_price = Decimal(request.POST.get('purchase_price', str(asset.purchase_price)))
            
            # expected_appreciation
            expected_appreciation_str = request.POST.get('expected_appreciation', '0').strip()
            asset.expected_appreciation = Decimal(expected_appreciation_str) if expected_appreciation_str else Decimal('0.00')
            
            # actual_market_value
            actual_market_value_str = request.POST.get('actual_market_value', '').strip()
            asset.actual_market_value = Decimal(actual_market_value_str) if actual_market_value_str else None
            
            asset.monthly_rent = Decimal(request.POST.get('monthly_rent', str(asset.monthly_rent or '0')))
            if purchase_date_str:
                potential_date = pd.to_datetime(purchase_date_str).date()
                if potential_date > timezone.localdate():
                    messages.error(request, "Purchase date cannot be in the future.")
                    return redirect('edit_other_asset', pk=pk)
                asset.purchase_date = potential_date
            asset.holder_name = request.POST.get('holder_name', '').strip()
            asset.asset_id = request.POST.get('asset_id', '').strip()
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
            interest = (loan.loan_amount_decimal * loan.interest_rate_decimal / 100) / 12
        else:
            # Reducing balance: based on current outstanding
            interest = (loan.current_outstanding * loan.interest_rate_decimal / 100) / 12
            
        interest = Decimal(str(interest)).quantize(Decimal('0.01'))
        
        # Principal component is EMI minus interest
        principal = loan.emi_amount_decimal - interest
        if principal < 0: principal = 0
        
        # If remaining principal is less than calculated principal, adjust
        cur_out = loan.current_outstanding
        if principal > cur_out:
            principal = cur_out
            # Optional: adjust amount or record as last EMI
            
        LoanPayment.objects.create(
            loan=loan,
            payment_type='EMI',
            amount=loan.emi_amount_decimal,
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
    target_user, is_family_view, is_consolidated = get_target_user(request)
    loans = Loan.objects.filter(user=target_user).order_by('-start_date')
    
    # Process auto EMIs before calculating totals
    for l in loans:
        if l.is_active:
            _process_auto_emis(l)
            
    total_loan_amount = float(sum(l.loan_amount_decimal for l in loans))
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
@prevent_duplicate_submissions
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
        form = LoanForm(initial={'next_emi_date': timezone.localdate()})
        
    return render(request, 'core/loan_form.html', {'form': form, 'action': 'Add'})

@login_required
@prevent_duplicate_submissions
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
    temp_date = loan.next_emi_date or (timezone.localdate() + relativedelta(months=1))
    
    for i in range(12):
        if temp_outstanding <= 0: break
        
        if loan.interest_type == 'Flat':
            interest = (float(loan.loan_amount_decimal) * float(loan.interest_rate_decimal) / 100) / 12
        else:
            interest = (temp_outstanding * float(loan.interest_rate_decimal) / 100) / 12
            
        principal = float(loan.emi_amount_decimal) - interest
        if principal > temp_outstanding:
            principal = temp_outstanding
            
        amortization.append({
            'date': temp_date,
            'emi': loan.emi_amount_decimal,
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
@prevent_duplicate_submissions
def add_loan_payment(request, pk):
    """Record a prepayment or manual payment."""
    loan = get_object_or_404(Loan, pk=pk, user=request.user)
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        date_str = request.POST.get('date')
        payment_date = pd.to_datetime(date_str).date() if date_str else timezone.localdate()
        
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

@ensure_csrf_cookie
def backtest_strategy_api(request):
    """API for historical backtesting of the investment strategy."""
    symbol = request.GET.get('symbol', '').strip().upper()
    start_date_str = request.GET.get('start_date', '2023-01-01')
    max_inv = float(request.GET.get('max_inv', '15000'))
    
    if not symbol:
        return JsonResponse({'error': 'Symbol is required'}, status=400)
    
    try:
        # Determine yfinance symbol
        yf_symbol = symbol
        if not any(x in symbol for x in ['^', '.', '=F']):
            yf_symbol = f"{symbol}.NS"
            
        t = yf.Ticker(yf_symbol)
        # Fetch 1y extra for 52W high baseline
        start_dt = pd.to_datetime(start_date_str)
        hist = t.history(start=start_dt - timedelta(days=365))
        if hist.empty:
            return JsonResponse({'error': f'No data found for symbol {symbol}'}, status=400)
            
        # Fix: Ensure start_dt has same timezone as hist.index to avoid comparison errors
        if hist.index.tz is not None and start_dt.tzinfo is None:
            start_dt = start_dt.tz_localize(hist.index.tz)
            
        sim_data = hist[hist.index >= start_dt]
        if sim_data.empty:
            return JsonResponse({'error': 'Start date is too recent for simulation data'}, status=400)

        # Simulation
        def get_factor_j_val(price, h52):
            if not h52 or h52 == 0: return 1.0
            diff = ((h52 - price) / h52) * 100
            if diff <= 2: return 0.5
            if diff <= 5: return 0.55
            if diff <= 8: return 0.6
            if diff <= 12: return 0.68
            if diff <= 18: return 0.75
            if diff <= 25: return 0.85
            if diff <= 35: return 0.92
            return 0.97

        def get_factor_i_val(pe):
            """PE Factor - same logic as portfolio get_factor_i()."""
            if pe is None or pe == 0: return 0.3
            pe = float(pe)
            if pe < 0: return 0.3333333333
            if pe == 50: return 1.0
            if pe > 50: return 50.0 / pe
            return 1.0

        # Fetch current PE ratio from yfinance (used as constant factor through simulation)
        try:
            ticker_info = t.info
            pe_ratio = ticker_info.get('trailingPE') or ticker_info.get('forwardPE') or 0
        except Exception:
            pe_ratio = 0
        factor_i = get_factor_i_val(pe_ratio)

        realized_profit = 0
        quantity = 0
        avg_cost = 0
        
        # Financial tracking
        gross_total_buys = 0 # Cumulative sum of all buy transactions
        capital_injected = 0 # Fresh money brought in from outside
        cash_balance = 0     # Liquidity from sells
        market_qty = 0       # Unit tracking for benchmark
        
        results = []
        
        for i, (dt, row) in enumerate(sim_data.iterrows()):
            price = float(row['Close'])
            prev_capital = capital_injected
            
            # Apply 5% annual interest on cash balance for the number of days since the last data point
            if i > 0 and cash_balance > 0:
                prev_dt = sim_data.index[i-1]
                # Calculate literal days passed (handles weekends/holidays)
                days_passed = (dt - prev_dt).days
                if days_passed > 0:
                    interest_rate = 0.05 / 365
                    interest_earned = cash_balance * interest_rate * days_passed
                    cash_balance += interest_earned
            # Calculate 52W High up to this day by looking back from the base history
            lookback = hist[hist.index < dt].tail(252)
            h52 = float(lookback['High'].max()) if not lookback.empty else price
            
            # Check for Sell Signal (22% Target)
            if quantity > 0:
                invested_val = quantity * avg_cost
                current_val = quantity * price
                unrealized_pct = ((current_val - invested_val) / invested_val) * 100
                
                # Suppress SELL if Realized Profit > Current Investment (keep averaging instead)
                if unrealized_pct >= 22.0 and realized_profit <= invested_val:
                    sell_proceeds = current_val
                    profit = sell_proceeds - invested_val
                    
                    # From profit booking, 2% of profit is deducted as expenses
                    realized_profit += profit * 0.98
                    cash_balance += sell_proceeds - (profit * 0.02)
                    
                    quantity = 0
                    avg_cost = 0

            # Calculate Buy Gap based on Strategy rules (matching portfolio formula)
            current_invested = quantity * avg_cost
            target_investment = (realized_profit * 0.93 - current_invested) + (max_inv * get_factor_j_val(price, h52) * factor_i)
            buy_gap = target_investment
            
            if buy_gap > 3000:
                buy_qty = int(buy_gap // price)
                if buy_qty > 0:
                    buy_cost = buy_qty * price
                    gross_total_buys += buy_cost
                    
                    # Funding the buy: use cash first, then inject capital
                    if cash_balance >= buy_cost:
                        cash_balance -= buy_cost
                    else:
                        additional_needed = buy_cost - cash_balance
                        capital_injected += additional_needed
                        cash_balance = 0

                    total_qty = quantity + buy_qty
                    avg_cost = float((quantity * avg_cost + buy_cost) / total_qty)
                    quantity = total_qty

            # Benchmark Logic: If capital was injected, "buy" the same amount in market portfolio
            if capital_injected > prev_capital:
                new_injection = capital_injected - prev_capital
                market_qty += float(new_injection / price)

            results.append({
                'date': dt.strftime('%Y-%m-%d'),
                'price': round(price, 2),
                'invested': round(quantity * avg_cost, 2),
                'current_value': round(quantity * price, 2),
                'realized_profit': round(realized_profit, 2),
                'cash_balance': round(cash_balance, 2),
                'total_wealth': round(quantity * price + cash_balance, 2),
                'market_wealth': round(market_qty * price, 2),
            })

        # Summary Metrics
        last_wealth = results[-1]['total_wealth']
        last_market_wealth = results[-1]['market_wealth']
        summary = {
            'total_invested': round(capital_injected, 2), # Correct: Basis is net capital put in
            'realized_profit': round(realized_profit, 2),
            'current_holdings_value': round(results[-1]['current_value'], 2),
            'total_wealth': round(last_wealth, 2),
            'net_profit': round(last_wealth - capital_injected, 2),
            'returns_pct': round(((last_wealth - capital_injected) / capital_injected * 100) if capital_injected > 0 else 0, 2),
            'market_returns_pct': round(((last_market_wealth - capital_injected) / capital_injected * 100) if capital_injected > 0 else 0, 2)
        }
        
        return JsonResponse({'summary': summary, 'results': results})
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def chatbot_response(request):
    """
    Handle chatbot queries with a knowledge base about FOLIUX.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip().lower()
            
            kb = {
                # Platform Basics
                "what is": "FOLIUX (FOLIUX Investment Tracking System) is a rules-based financial platform designed for disciplined wealth creation. It helps you manage multiple asset classes with precision using FIFO accounting.",
                "foliux": "FOLIUX is your central hub for investment management. It uses data-driven signals to remove emotions from investing, focusing on automated 'Buy' and 'Sell' advice.",
                "security": "FOLIUX prioritizes your data security. Your sensitive investment data is encrypted (using Fernet encryption), and we use secure OTP-based authentication for logins and family linking.",
                
                # Portfolio & Data Management
                "how to add": "You can add items by clicking 'Add Instrument' on any dashboard. For stocks, you can also use 'Buy Stock' to add a single lot or 'Upload Portfolio' for bulk entry.",
                "upload": "To upload in bulk, go to the Stock Dashboard and click 'Upload Portfolio'. We support .csv and .xlsx files from major brokers like Zerodha, Groww, etc.",
                "excel": "You can download your portfolio as an Excel file using the 'Export' button on the Stock Dashboard for offline analysis.",
                "google sheets": "FOLIUX can sync with Google Sheets for real-time data ingestion. Check the 'Sync' options on the dashboard for more details.",
                "fifo": "FOLIUX uses First-In-First-Out (FIFO) logic to track individual stock lots. This ensures accurate P&L calculation and tax planning by matching your oldest buys with your sales.",
                "lots": "Lot-based tracking means every purchase of a stock is treated separately. This helps you see the profit of each specific entry instead of just a consolidated average.",
                
                # Signals & Strategy
                "signals": "Signals are rule-based indicators: 'BUY' (price is low/attractive), 'SELL' (target reached), 'HOLD' (maintain position), and 'REDUCE' (over-allocation detected).",
                "rules": "Our rules are based on predefined strategies like the 5% Index Strategy. These signals help you stay disciplined and avoid emotional trading.",
                "strategy": "The Strategy page explains our frameworks: 'FlexiMultiInvest' (Broad Market), 'NiftyQuant' (Top 50), and 'Pyramiding' (Thematic/Sectoral).",
                "quant": "NiftyQuant is a strategy focusing on high-liquidity Nifty 50 stocks with specific rebalancing rules.",
                "flexi": "FlexiMultiInvest uses broad-market ETFs to provide diversified exposure with rule-based entry points.",
                "pyramid": "Pyramiding focuses on building positions in strong sectoral trends and ETFs like ITBEES, BANKBEES, etc.",
                "backtest": "The Strategic Simulation Lab (Backtester) on the Strategy page allows you to test how these rules would have performed in the past.",
                
                # Asset Classes
                "stocks": "The Stock Dashboard tracks your equity investments, providing real-time P&L, signal badges, and allocation charts.",
                "mutual funds": "MF helps you track Mutual Funds, SIPs, and goal-based investments with automated sell-trigger alerts.",
                "mf": "Mutual Fund provides advice on when to sell (at 22% profit target) and tracks your monthly SIP executions automatically.",
                "nps": "NPS tracks your National Pension System funds and NAVs across various fund managers (Scheme E, C, G).",
                "coin": "The Coin Dashboard tracks digital assets and cryptocurrencies with live price updates and transaction history.",
                "fd": "The FD module tracks Fixed Deposits, showing maturity dates, interest rates, and total monthly interest income.",
                "loan": "The Loan module manages your EMIs, tracking how much of each payment goes toward principal versus interest.",
                "ipo": "The IPO Tracker shows upcoming and active Initial Public Offerings with listing dates and subscription statuses.",
                
                # Account & Features
                "family": "Family Linking allows you to view your family members' portfolios in read-only mode after they verify your request with an OTP.",
                "profile": "In 'Edit Profile', you can set your investment limits, update your photo, and toggle between Crore/Lakh and Million/Billion numbering systems.",
                "otp": "We use OTPs for secure actions like registration, password resets, and linking family accounts for maximum security.",
                "contact": "For support or bug reports, please reach out to the platform administrator via the support email in the footer.",
                
                # Contextual/Help
                "help": "You can ask me about: how to add stocks, how signals work, what is FIFO, how to link family, or details about MF and NPS modules.",
                "hello": "Hello! I am your FOLIUX Assistant. How can I help you manage your wealth today?",
                "hi": "Hi there! Welcome to FOLIUX. I'm here to help you navigate your portfolio and strategies.",
                "thanks": "You're welcome! Happy investing with FOLIUX.",
            }
            
            reply = "I'm sorry, I don't have a specific answer for that. FOLIUX is a rule-based investment system. You can ask about stocks, FIFO, signals, backtesting, or our asset modules like MF, NPS, and Loans."
            
            # 1. SPECIAL CASE: Market Price Queries
            price_query_words = ['price', 'value', 'quote', 'rate', 'ltp', 'change', 'nifty', 'sensex', 'banknifty', '%', 'percentage']
            price_match_found = False
            
            if any(word in user_message for word in price_query_words):
                tickers = MarketTicker.objects.all()
                matching_ticker = None
                
                # Direct match in MarketTicker (includes major indices and some stocks)
                for t in tickers:
                    if t.name.lower() in user_message:
                        matching_ticker = t
                        break
                
                # Heuristic matches for common indices
                if not matching_ticker:
                    if 'nifty 50' in user_message or ( 'nifty' in user_message and 'bank' not in user_message and 'it' not in user_message):
                        matching_ticker = tickers.filter(name__icontains='NIFTY 50').first()
                    elif 'bank' in user_message and 'nifty' in user_message:
                        matching_ticker = tickers.filter(name__icontains='NIFTY BANK').first()
                    elif 'it' in user_message and 'nifty' in user_message:
                        matching_ticker = tickers.filter(name__icontains='NIFTY IT').first()
                    elif 'sensex' in user_message:
                        matching_ticker = tickers.filter(name__icontains='SENSEX').first()

                if matching_ticker:
                    direction = "up" if matching_ticker.change >= 0 else "down"
                    sign = "+" if matching_ticker.change >= 0 else ""
                    reply = f"The current price of **{matching_ticker.name}** is **₹{matching_ticker.price:,.2f}**. It is {direction} by **{sign}{matching_ticker.change:,.2f} ({sign}{matching_ticker.percent_change:,.2f}%)** today."
                    price_match_found = True
                else:
                    # Check Instruments (Specific stock symbols)
                    words = user_message.translate(str.maketrans('', '', '?!.,')).split()
                    for word in words:
                        if len(word) < 3: continue
                        instr = Instrument.objects.filter(symbol__iexact=word.upper()).first()
                        if instr:
                            direction = "up" if instr.price_change >= 0 else "down"
                            sign = "+" if instr.price_change >= 0 else ""
                            pct = (float(instr.price_change) / float(instr.previous_close) * 100) if instr.previous_close and instr.previous_close != 0 else 0
                            reply = f"The current price of **{instr.symbol} ({instr.name})** is **₹{instr.last_price:,.2f}**. It is {direction} by **{sign}{instr.price_change:,.2f} ({sign}{pct:,.2f}%)** today."
                            price_match_found = True
                            break
            
            if not price_match_found:
                # 2. Try Database Match (3-word match logic)
                user_words = set(user_message.translate(str.maketrans('', '', '?!.,')).split())
                knowledge_base = ChatbotKnowledge.objects.all()
                
                best_db_match = None
                max_overlap = 0
                
                for entry in knowledge_base:
                    q_words = set(entry.question.lower().translate(str.maketrans('', '', '?!.,')).split())
                    overlap = len(user_words.intersection(q_words))
                    if overlap >= 3 and overlap > max_overlap:
                        max_overlap = overlap
                        best_db_match = entry.answer
                
                if best_db_match:
                    reply = best_db_match
                else:
                    # 3. Fallback to Hardcoded KB if no DB match
                    sorted_keys = sorted(kb.keys(), key=len, reverse=True)
                    for key in sorted_keys:
                        if key in user_message:
                            reply = kb[key]
                            break
            
            # Send notification email to admin
            try:
                user_info = f"User: {request.user.username} ({request.user.email})" if request.user.is_authenticated else "Guest User"
                email_subject = f"FOLIUX Assistant Inquiry"
                email_body = f"An inquiry was made to the FOLIUX Assistant.\n\n{user_info}\nQuestion: {user_message}\n\nProvided Answer: {reply}\n\nTimestamp: {timezone.now()}"
                
                import threading
                def _run_send_mail():
                    try:
                        send_mail(
                            email_subject,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            ['jitendra.kar@gmail.com'],
                            fail_silently=True
                        )
                    except Exception:
                        pass
                
                threading.Thread(target=_run_send_mail).start()
                
                # Append notice to reply
                reply += "\n\n---\nNote: Your query is recorded and our team is notified. We’ll contact you if needed—please share your email ID and mobile number."
                
            except Exception as e:
                logger.error(f"Chatbot email notification failed: {e}")

            return JsonResponse({'reply': reply})
        except Exception as e:
            logger.exception("Chatbot response error:")
            return JsonResponse({'reply': f"Error: {str(e)}"}, status=500)
            
    return JsonResponse({'error': 'POST required'}, status=405)

@login_required
@csrf_exempt
def toggle_hidden_signal(request):
    if request.method == 'POST':
        import json as _json
        try:
            body = _json.loads(request.body)
            instrument_id = body.get('instrument_id')
            action_type = body.get('action') # 'hide' or 'unhide'
            
            from core.models import Instrument, HiddenSignal
            inst = get_object_or_404(Instrument, id=instrument_id)
            
            if action_type == 'hide':
                HiddenSignal.objects.get_or_create(user=request.user, instrument=inst)
                return JsonResponse({'status': 'ok', 'message': f'Hidden {inst.symbol} from buying signals.'})
            elif action_type == 'unhide':
                HiddenSignal.objects.filter(user=request.user, instrument=inst).delete()
                return JsonResponse({'status': 'ok', 'message': f'Unhidden {inst.symbol}.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

@login_required
def request_reset_otp(request):
    user = request.user
    if not user.email:
        messages.error(request, "No email address found for your account. Please update your profile first.")
        return redirect('edit_profile')
    
    # Generate 6-digit OTP
    code = str(random.randint(100000, 999999))
    
    # Save OTP
    OTP.objects.filter(user=user).delete()
    OTP.objects.create(user=user, code=code)
    
    # Send Email
    try:
        subject = "Account Reset Verification Code - FOLIUX"
        message = f"You have requested to reset all data for your FOLIUX account ({user.email}).\n\nYour 6-digit verification code is: {code}\n\nThis code is valid for 10 minutes. If you did not request this, please ignore this email."
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        
        request.session['resetting_user_id'] = user.id
        messages.success(request, f"A 6-digit verification code has been sent to {user.email}")
        return redirect('verify_reset_otp')
    except Exception as e:
        logger.error(f"Error sending reset OTP: {e}")
        messages.error(request, "Failed to send verification code. Please try again later.")
        return redirect('edit_profile')

@login_required
def verify_reset_otp(request):
    user_id = request.session.get('resetting_user_id')
    if not user_id or user_id != request.user.id:
        return redirect('edit_profile')
        
    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()
        otp_obj = OTP.objects.filter(user=request.user).order_by('-created_at').first()
        
        if otp_obj and str(otp_obj.code) == str(otp_code) and otp_obj.is_valid():
            # VERIFIED - Perform Reset
            reset_account_data(request.user)
            
            # Cleanup session
            del request.session['resetting_user_id']
            OTP.objects.filter(user=request.user).delete()
            
            messages.success(request, "Your account has been reset to the initial signup state.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid or expired verification code.")
    
    return render(request, 'core/verify_reset_otp.html')

def reset_account_data(user):
    """Helper to delete all user-related data and reset profile to defaults."""
    # List of models to clear (ForeignKey to user)
    models_to_clear = [
        Portfolio, PnLStatement, Transaction, Watchlist, Dividend,
        InvestmentGoal, SignalNotificationState, FinancialYearData,
        MFPortfolio, MFTransaction, CoinPortfolio, CoinTransaction,
        NPSPortfolio, NPSTransaction, FixedAsset, OtherAsset,
        Loan, MFSIP, PortfolioValueHistory, HiddenSignal
    ]
    
    # Also FamilyLink (both sides)
    FamilyLink.objects.filter(user=user).delete()
    FamilyLink.objects.filter(family_user=user).delete()
    
    # Delete related records
    for model in models_to_clear:
        try:
            model.objects.filter(user=user).delete()
        except Exception as e:
            logger.error(f"Error clearing {model.__name__} for user {user.username}: {e}")

    # Reset Profile to defaults
    try:
        profile = user.profile
        # Reset numeric fields to defaults from model definition
        profile.investor_type = 'moderate'
        profile.initial_investment_limit = 15000.00
        profile.mf_investment_limit = 100000.00
        profile.coin_investment_limit = 15000.00
        profile.equity_profit_expectation = 22.00
        profile.mf_profit_expectation = 22.00
        profile.coin_profit_expectation = 22.00
        profile.equity_fixed_charge = 0.00
        profile.equity_brokerage_pct = 0.0000
        profile.intraday_fixed_charge = 0.00
        profile.intraday_brokerage_pct = 0.0000
        profile.financial_goal = 10000000.00
        
        # Delete profile picture if exists
        if profile.profile_picture:
            try:
                profile.profile_picture.delete(save=False)
            except Exception:
                pass
            profile.profile_picture = None
            
        profile.save()
    except Exception as e:
        logger.error(f"Error resetting profile for user {user.username}: {e}")


def wealth_calculators(request):
    """Render the FOLIUX Wealth Studio calculators suite."""
    return render(request, 'core/calc.html')


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
import re
from .ais_importer import decrypt_ais_json, parse_and_import_ais

import logging
logger = logging.getLogger(__name__)

def extract_fy_from_filename(filename):
    match = re.search(r'(\d{4}-\d{2,4})', filename)
    if match:
        return match.group(1)
    return None

@login_required
@require_POST
def import_ais_api(request):
    if 'ais_file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400)
    
    ais_file = request.FILES['ais_file']
    password = request.POST.get('password', '').strip()
    duplicate_action = request.POST.get('duplicate_action', '')
    
    if ais_file.size == 0:
        return JsonResponse({'status': 'error', 'message': 'Empty File.'}, status=400)
    if not (ais_file.name.lower().endswith('.json') or ais_file.name.lower().endswith('.zip')):
        return JsonResponse({'status': 'error', 'message': 'Accept only .json or .zip files.'}, status=400)

    fy = extract_fy_from_filename(ais_file.name)
    if not fy:
        return JsonResponse({'status': 'error', 'message': 'Unsupported AIS Version: Could not determine Financial Year from filename. Expected format like XXXPK3598X_2025-26_AIS_01072026.json or .zip.'}, status=400)

    try:
        content_bytes = ais_file.read()
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Corrupted File.'}, status=400)

    try:
        decrypted_text = decrypt_ais_json(content_bytes, password)
    except ValueError as e:
        logger.error(f"AIS decrypt ValueError: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        import traceback
        logger.error(f"AIS decrypt Exception: {e}\n{traceback.format_exc()}")
        return JsonResponse({'status': 'error', 'message': f'Decryption failed: {e}'}, status=400)

    try:
        counts_or_duplicate, err_msg = parse_and_import_ais(request.user, decrypted_text, fy, duplicate_action=duplicate_action)
    except Exception as e:
        import traceback
        logger.error(f"AIS parse/import Exception: {e}\n{traceback.format_exc()}")
        return JsonResponse({'status': 'error', 'message': f'Import failed: {e}'}, status=500)

    if err_msg:
        return JsonResponse({'status': 'error', 'message': err_msg}, status=400)

    if counts_or_duplicate and 'status' in counts_or_duplicate and counts_or_duplicate['status'] == 'duplicate_detected':
        return JsonResponse({
            'status': 'duplicate_detected',
            'financial_year': counts_or_duplicate['financial_year'],
            'message': f"Existing records found for Financial Year {counts_or_duplicate['financial_year']}."
        })

    return JsonResponse({
        'status': 'success',
        'financial_year': fy,
        'counts': counts_or_duplicate
    })


@login_required
def ais_dashboard(request):
    from .models import IncomeTaxProfile
    user = request.user
    available_fys = list(IncomeTaxProfile.objects.filter(user=user).values_list('financial_year', flat=True).distinct().order_by('-financial_year'))
    selected_fy = request.GET.get('fy', available_fys[0] if available_fys else '')
    return render(request, 'core/ais_dashboard.html', {
        'available_fys': available_fys,
        'selected_fy': selected_fy,
    })


@login_required
def ais_data_api(request):
    from decimal import Decimal
    from django.forms.models import model_to_dict
    from .models import (
        IncomeTaxProfile, IncomeTaxTds, IncomeTaxSalary, IncomeTaxInterest,
        IncomeTaxDividend, IncomeTaxEquity, IncomeTaxMutualFund, IncomeTaxSft,
        IncomeTaxTaxPaid, IncomeTaxRefund, IncomeTaxDemand, IncomeTaxOther
    )
    
    fy = request.GET.get('fy')
    if not fy:
        return JsonResponse({'status': 'error', 'message': 'Missing Financial Year parameter.'}, status=400)
        
    user = request.user
    
    def serialize_qs(qs, exclude_json=True):
        exclude = ['user']
        if exclude_json:
            exclude.append('json_reference')
        return [model_to_dict(obj, exclude=exclude) for obj in qs]
        
    data = {
        'profile': serialize_qs(IncomeTaxProfile.objects.filter(user=user, financial_year=fy)),
        'tds': serialize_qs(IncomeTaxTds.objects.filter(user=user, financial_year=fy)),
        'salary': serialize_qs(IncomeTaxSalary.objects.filter(user=user, financial_year=fy)),
        'interest': serialize_qs(IncomeTaxInterest.objects.filter(user=user, financial_year=fy)),
        'dividend': serialize_qs(IncomeTaxDividend.objects.filter(user=user, financial_year=fy)),
        'equity': serialize_qs(IncomeTaxEquity.objects.filter(user=user, financial_year=fy), exclude_json=False),
        'mutual_fund': serialize_qs(IncomeTaxMutualFund.objects.filter(user=user, financial_year=fy), exclude_json=False),
        'sft': serialize_qs(IncomeTaxSft.objects.filter(user=user, financial_year=fy)),
        'tax_payment': serialize_qs(IncomeTaxTaxPaid.objects.filter(user=user, financial_year=fy)),
        'refund': serialize_qs(IncomeTaxRefund.objects.filter(user=user, financial_year=fy)),
        'demand': serialize_qs(IncomeTaxDemand.objects.filter(user=user, financial_year=fy)),
        'other': serialize_qs(IncomeTaxOther.objects.filter(user=user, financial_year=fy)),
    }
    
    import datetime
    for key, items in data.items():
        for item in items:
            for k, v in list(item.items()):
                if isinstance(v, (datetime.datetime, datetime.date)):
                    item[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    item[k] = float(v)
                    
    return JsonResponse({'status': 'success', 'financial_year': fy, 'data': data})


@login_required
@require_POST
def update_theme_preference(request):
    try:
        data = json.loads(request.body)
        theme = data.get('theme')
        if theme in ['light', 'dark']:
            profile = request.user.profile
            profile.theme = theme
            profile.save()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Invalid theme value'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =========================================================================
# CASHFLOW MODULE VIEW CONTROLLERS & HELPERS
# =========================================================================

def get_available_financial_years(user):
    from datetime import date
    from .models import CashFlowEntry, MFTransaction, PnLStatement
    today = date.today()
    start_year = 2023 # fallback default
    
    # Check earliest CashFlowEntry
    earliest_entry = CashFlowEntry.objects.filter(user=user).order_by('date').first()
    if earliest_entry:
        start_year = min(start_year, earliest_entry.date.year)
        
    # Check earliest MFTransaction
    earliest_mf = MFTransaction.objects.filter(user=user).order_by('date').first()
    if earliest_mf:
        start_year = min(start_year, earliest_mf.date.year)
        
    # Check earliest PnLStatement
    earliest_pnl = PnLStatement.objects.filter(user=user).order_by('exit_date').first()
    if earliest_pnl:
        start_year = min(start_year, earliest_pnl.exit_date.year)
        
    current_year = today.year
    if today.month < 4:
        current_year -= 1
        
    fys = []
    for y in range(start_year, current_year + 2):
        fys.append(f"{y}-{y+1}")
    return sorted(list(set(fys)), reverse=True)


def fy_to_dates(fy_str):
    from datetime import date
    try:
        parts = fy_str.split('-')
        start_year = int(parts[0])
        end_year = int(parts[1])
        return date(start_year, 4, 1), date(end_year, 3, 31)
    except Exception:
        today = date.today()
        y = today.year
        if today.month < 4:
            y -= 1
        return date(y, 4, 1), date(y+1, 3, 31)


def get_fy_cashflow_details(user, fy_str, months=None, income_types=None, expense_categories=None, investment_types=None, current_date=None):
    from datetime import date, timedelta
    from collections import defaultdict
    from calendar import monthrange
    from decimal import Decimal
    import logging
    from .models import CashFlowEntry, FixedAsset, PnLStatement, MFTransaction, Loan, LoanPayment, OtherAsset
    
    logger = logging.getLogger(__name__)
    start_date, end_date = fy_to_dates(fy_str)
    
    if current_date is None:
        from django.utils import timezone
        current_date = timezone.localtime(timezone.now()).date()
        
    last_day_of_current_month = monthrange(current_date.year, current_date.month)[1]
    current_month_end = date(current_date.year, current_date.month, last_day_of_current_month)
    
    if start_date > current_month_end:
        return [], {
            'salary': Decimal('0'),
            'other_income': Decimal('0'),
            'fd_interest': Decimal('0'),
            'pf_interest': Decimal('0'),
            'other_interest': Decimal('0'),
            'stock_realized': Decimal('0'),
            'mf_realized': Decimal('0'),
            'daily_expense': Decimal('0'),
            'emi': Decimal('0'),
            'sip': Decimal('0'),
            'other_expense': Decimal('0'),
            'total_income': Decimal('0'),
            'total_expenses': Decimal('0'),
            'net_cashflow': Decimal('0'),
        }
        
    if end_date > current_month_end:
        end_date = current_month_end
    
    # Convert filters to standard lists of upper-case strings/integers
    if months:
        months = [int(m) for m in months]
    if income_types:
        income_types = [t.upper() for t in income_types]
    if expense_categories:
        expense_categories = [c.upper() for c in expense_categories]
    if investment_types:
        investment_types = [t.upper() for t in investment_types]
        
    # Prepare months list
    months_list = []
    curr = start_date
    while curr <= end_date:
        m_start = curr
        last_day = monthrange(curr.year, curr.month)[1]
        m_end = date(curr.year, curr.month, last_day)
        if not months or curr.month in months:
            months_list.append((curr.year, curr.month, m_start, m_end))
        curr = m_end + timedelta(days=1)
        
    # Pre-process: Trigger auto EMIs and SIPs to catch up
    try:
        for l in Loan.objects.filter(user=user, is_active=True):
            _process_auto_emis(l)
        _process_auto_mf_sips(user)
    except Exception as e:
        logger.error(f"Error processing auto EMIs/SIPs: {e}")
        
    # 1. Fetch manual entries
    entries = CashFlowEntry.objects.filter(user=user, date__range=(start_date, end_date))
    manual_by_month = defaultdict(lambda: defaultdict(Decimal))
    for entry in entries:
        if entry.entry_type == 'INCOME':
            if income_types and entry.category not in income_types:
                continue
        elif entry.entry_type == 'EXPENSE':
            if expense_categories and entry.category not in expense_categories:
                continue
        elif entry.entry_type == 'INVESTMENT':
            if investment_types and entry.category not in investment_types:
                continue
                
        key = (entry.date.year, entry.date.month)
        manual_by_month[key][entry.category] += entry.amount
        
    # 1.5 Add other assets monthly rent automatically
    if not income_types or 'RENTAL_INCOME' in income_types:
        other_assets = list(OtherAsset.objects.filter(user=user))
        for y, m, m_start, m_end in months_list:
            key = (y, m)
            for asset in other_assets:
                monthly_rent = asset.monthly_rent or Decimal('0')
                if asset.purchase_date <= m_end and monthly_rent > 0:
                    manual_by_month[key]['RENTAL_INCOME'] += monthly_rent
                    
    # 2. Fixed Assets
    fixed_assets = list(FixedAsset.objects.filter(user=user))
    interest_by_month = defaultdict(lambda: defaultdict(Decimal))
    for y, m, m_start, m_end in months_list:
        key = (y, m)
        day_before = m_start - timedelta(days=1)
        for asset in fixed_assets:
            if asset.investment_date > m_end:
                interest = Decimal('0')
            else:
                # If the asset was invested during this month, the starting value is its principal/deposit
                if asset.investment_date >= m_start:
                    val_start = asset.invested_amount_decimal
                else:
                    val_start = asset.value_at_date(day_before)
                val_end = asset.value_at_date(m_end)
                interest = val_end - val_start
                if asset.asset_type == 'RD':
                    if not asset.maturity_date or asset.maturity_date >= m_start:
                        interest -= (asset.monthly_deposit or Decimal('0'))
                interest = max(Decimal('0'), interest)
            
            # Apply income type filter for interest income
            if income_types and 'INTEREST_INCOME' not in income_types:
                interest = Decimal('0')
                
            if asset.asset_type in ['FD', 'RD']:
                interest_by_month[key]['FD'] += interest
            elif asset.asset_type in ['PPF', 'EPF']:
                interest_by_month[key]['PF'] += interest
            elif asset.asset_type == 'Other':
                interest_by_month[key]['Other'] += interest
                
    # 3. Stock Realized Profit
    pnl_records = PnLStatement.objects.filter(user=user, exit_date__range=(start_date, end_date))
    stock_profit_by_month = defaultdict(Decimal)
    for p in pnl_records:
        if income_types and 'STOCK_PROFIT' not in income_types:
            continue
        key = (p.exit_date.year, p.exit_date.month)
        stock_profit_by_month[key] += p.realized_profit
        
    # 4. Mutual Fund Realized Profit (using FIFO on all user transactions)
    mf_txs = MFTransaction.objects.filter(user=user).order_by('date', 'created_at')
    buy_lots = defaultdict(list)
    mf_profit_by_month = defaultdict(Decimal)
    for tx in mf_txs:
        fid = tx.fund_id
        if tx.transaction_type == 'BUY':
            buy_lots[fid].append({'units': tx.units, 'price': tx.price})
        elif tx.transaction_type == 'SELL':
            sell_units = tx.units
            cost = Decimal('0')
            while sell_units > 0 and buy_lots[fid]:
                lot = buy_lots[fid][0]
                matched = min(lot['units'], sell_units)
                cost += matched * lot['price']
                lot['units'] -= matched
                sell_units -= matched
                if lot['units'] <= 0:
                    buy_lots[fid].pop(0)
            profit = (tx.units * tx.price) - cost
            if start_date <= tx.date <= end_date:
                if income_types and 'MUTUAL_FUND_PROFIT' not in income_types:
                    continue
                key = (tx.date.year, tx.date.month)
                mf_profit_by_month[key] += profit
                
    # 5. Loan EMIs
    payments = LoanPayment.objects.filter(loan__user=user, payment_type='EMI', date__range=(start_date, end_date))
    emi_by_month = defaultdict(Decimal)
    for p in payments:
        key = (p.date.year, p.date.month)
        emi_by_month[key] += p.amount_decimal
        
    # 6. MF SIP investments
    sip_txs = MFTransaction.objects.filter(user=user, is_sip=True, transaction_type='BUY', date__range=(start_date, end_date))
    sip_by_month = defaultdict(Decimal)
    for tx in sip_txs:
        if investment_types and 'SIP' not in investment_types and 'MUTUAL_FUNDS' not in investment_types:
            continue
        key = (tx.date.year, tx.date.month)
        sip_by_month[key] += tx.units * tx.price
        
    # Assemble monthly breakdown
    monthly_data = []
    fy_totals = {
        'salary': Decimal('0'),
        'other_income': Decimal('0'),
        'fd_interest': Decimal('0'),
        'pf_interest': Decimal('0'),
        'other_interest': Decimal('0'),
        'stock_realized': Decimal('0'),
        'mf_realized': Decimal('0'),
        'daily_expense': Decimal('0'),
        'emi': Decimal('0'),
        'sip': Decimal('0'),
        'other_expense': Decimal('0'),
        'total_income': Decimal('0'),
        'total_expenses': Decimal('0'),
        'net_cashflow': Decimal('0'),
    }
    
    import calendar
    for y, m, m_start, m_end in months_list:
        key = (y, m)
        salary = manual_by_month[key]['SALARY']
        other_income = (
            manual_by_month[key]['OTHER_INCOME'] +
            manual_by_month[key]['RENTAL_INCOME'] +
            manual_by_month[key]['DIVIDEND_INCOME'] +
            manual_by_month[key]['INTEREST_INCOME']
        )
        
        daily_expense = (
            manual_by_month[key]['DAILY_EXPENSE'] +
            manual_by_month[key]['FOOD'] +
            manual_by_month[key]['GROCERIES'] +
            manual_by_month[key]['TRANSPORTATION'] +
            manual_by_month[key]['MEDICAL'] +
            manual_by_month[key]['ENTERTAINMENT'] +
            manual_by_month[key]['SHOPPING']
        )
        
        other_expense = (
            manual_by_month[key]['OTHER_EXPENSE'] +
            manual_by_month[key]['RENT'] +
            manual_by_month[key]['UTILITIES'] +
            manual_by_month[key]['EDUCATION'] +
            manual_by_month[key]['TRAVEL']
        )
        
        manual_investment = (
            manual_by_month[key]['SIP'] +
            manual_by_month[key]['MUTUAL_FUNDS'] +
            manual_by_month[key]['STOCKS'] +
            manual_by_month[key]['FD'] +
            manual_by_month[key]['PPF'] +
            manual_by_month[key]['EPF'] +
            manual_by_month[key]['NPS'] +
            manual_by_month[key]['BONDS'] +
            manual_by_month[key]['GOLD'] +
            manual_by_month[key]['REAL_ESTATE'] +
            manual_by_month[key]['OTHER_INVESTMENTS']
        )
        
        fd_int = interest_by_month[key]['FD']
        pf_int = interest_by_month[key]['PF']
        other_int = interest_by_month[key]['Other']
        
        stk_prof = stock_profit_by_month[key]
        mf_prof = mf_profit_by_month[key]
        
        emi_val = emi_by_month[key]
        sip_val = sip_by_month[key] + manual_investment
        
        total_inc = salary + fd_int + pf_int + other_int + stk_prof + mf_prof + other_income
        total_exp = daily_expense + emi_val + sip_val + other_expense
        net_cf = total_inc - total_exp
        
        month_name = calendar.month_name[m]
        
        m_stats = {
            'year': y,
            'month': m,
            'month_name': f"{month_name} {y}",
            'salary': salary,
            'other_income': other_income,
            'fd_interest': fd_int,
            'pf_interest': pf_int,
            'other_interest': other_int,
            'stock_realized': stk_prof,
            'mf_realized': mf_prof,
            'daily_expense': daily_expense,
            'emi': emi_val,
            'sip': sip_val,
            'other_expense': other_expense,
            'total_income': total_inc,
            'total_expenses': total_exp,
            'net_cashflow': net_cf,
        }
        monthly_data.append(m_stats)
        
        # Add to FY totals
        for k in fy_totals:
            if k in m_stats:
                fy_totals[k] += m_stats[k]
                
    return monthly_data, fy_totals


@login_required
def cashflow_dashboard(request):
    """Dashboard for Monthly and Financial Year-wise CashFlow."""
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    # Selected Financial Year
    from datetime import date
    import calendar
    today = date.today()
    y = today.year
    if today.month < 4:
        y -= 1
    default_fy = f"{y}-{y+1}"
    
    # Retrieve or clear session filters
    session_filters = request.session.get('cashflow_filters', {})
    
    if 'reset_filters' in request.GET:
        session_filters = {}
        request.session['cashflow_filters'] = {}
        from django.shortcuts import redirect as _redirect
        return _redirect('cashflow_dashboard')
    elif 'apply_filters' in request.GET or any(k in request.GET for k in ['months', 'income_types', 'expense_categories', 'investment_types']):
        session_filters = {
            'months': request.GET.getlist('months'),
            'income_types': request.GET.getlist('income_types'),
            'expense_categories': request.GET.getlist('expense_categories'),
            'investment_types': request.GET.getlist('investment_types'),
        }
        request.session['cashflow_filters'] = session_filters

    fy_str = request.GET.get('fy')
    if fy_str:
        session_filters['fy'] = fy_str
        request.session['cashflow_filters'] = session_filters
    else:
        fy_str = session_filters.get('fy', default_fy)
        
    months = session_filters.get('months', [])
    income_types = session_filters.get('income_types', [])
    expense_categories = session_filters.get('expense_categories', [])
    investment_types = session_filters.get('investment_types', [])
    
    # Fetch Data
    monthly_data, fy_totals = get_fy_cashflow_details(
        target_user, fy_str,
        months=months,
        income_types=income_types,
        expense_categories=expense_categories,
        investment_types=investment_types
    )
    fys = get_available_financial_years(target_user)
    
    # Recent Manual Entries in this FY
    from .models import CashFlowEntry
    start_date, end_date = fy_to_dates(fy_str)
    recent_entries = CashFlowEntry.objects.filter(
        user=target_user,
        date__range=(start_date, end_date)
    )
    if months:
        recent_entries = recent_entries.filter(date__month__in=[int(m) for m in months])
    if income_types or expense_categories or investment_types:
        from django.db.models import Q
        q_filter = Q()
        if income_types:
            q_filter |= Q(entry_type='INCOME', category__in=[t.upper() for t in income_types])
        if expense_categories:
            q_filter |= Q(entry_type='EXPENSE', category__in=[c.upper() for c in expense_categories])
        if investment_types:
            q_filter |= Q(entry_type='INVESTMENT', category__in=[t.upper() for t in investment_types])
        recent_entries = recent_entries.filter(q_filter)
    recent_entries = recent_entries.order_by('-date', '-created_at')[:20]
    
    # Category and Entry Types Choices
    entry_choices = CashFlowEntry.ENTRY_TYPES
    category_choices = CashFlowEntry.CATEGORIES
    
    INCOME_CHOICES = [
        ('SALARY', 'Salary'),
        ('RENTAL_INCOME', 'Rental Income'),
        ('INTEREST_INCOME', 'Interest (FD, PF, etc.)'),
        ('DIVIDEND_INCOME', 'Dividend Income'),
        ('STOCK_PROFIT', 'Stock Profit'),
        ('MUTUAL_FUND_PROFIT', 'Mutual Fund Profit'),
        ('OTHER_INCOME', 'Other Income'),
    ]

    EXPENSE_CHOICES = [
        ('FOOD', 'Food'),
        ('GROCERIES', 'Groceries & Vegetables'),
        ('RENT', 'Rent'),
        ('UTILITIES', 'Utilities'),
        ('TRANSPORTATION', 'Transportation'),
        ('MEDICAL', 'Medical'),
        ('ENTERTAINMENT', 'Entertainment / Movies'),
        ('SHOPPING', 'Shopping'),
        ('EDUCATION', 'Education'),
        ('TRAVEL', 'Travel'),
        ('DAILY_EXPENSE', 'Daily Expense'),
        ('OTHER_EXPENSE', 'Other Expense'),
    ]

    INVESTMENT_CHOICES = [
        ('SIP', 'SIP'),
        ('MUTUAL_FUNDS', 'Mutual Funds'),
        ('STOCKS', 'Stocks'),
        ('FD', 'Fixed Deposit (FD)'),
        ('PPF', 'PPF'),
        ('EPF', 'EPF/PF'),
        ('NPS', 'NPS'),
        ('BONDS', 'Bonds'),
        ('GOLD', 'Gold'),
        ('REAL_ESTATE', 'Real Estate'),
        ('OTHER_INVESTMENTS', 'Other Investments'),
    ]
    
    context = {
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
        'monthly_data': monthly_data,
        'fy_totals': fy_totals,
        'fys': fys,
        'selected_fy': fy_str,
        'recent_entries': recent_entries,
        'entry_choices': entry_choices,
        'category_choices': category_choices,
        
        # Filter fields passed to template
        'active_months': months,
        'active_income_types': income_types,
        'active_expense_categories': expense_categories,
        'active_investment_types': investment_types,
        'income_filter_choices': INCOME_CHOICES,
        'expense_filter_choices': EXPENSE_CHOICES,
        'investment_filter_choices': INVESTMENT_CHOICES,
        'month_choices': [(str(i), calendar.month_name[i]) for i in range(1, 13)],
    }
    return render(request, 'core/cashflow_dashboard.html', context)


@login_required
@prevent_duplicate_submissions
def add_cashflow_entry(request):
    """Add a manual income or expense cashflow entry."""
    if request.method == 'POST':
        target_user, is_family_view, is_consolidated = get_target_user(request)
        if is_consolidated:
            messages.error(request, "Cannot add entries in consolidated view.")
            return redirect('cashflow_dashboard')
            
        from decimal import Decimal
        from .models import CashFlowEntry
        
        date_str = request.POST.get('date')
        entry_type = request.POST.get('entry_type')
        category = request.POST.get('category')
        amount_str = request.POST.get('amount')
        description = request.POST.get('description', '').strip()
        fy_str = request.POST.get('fy', '')
        
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except Exception:
            messages.error(request, "Invalid amount provided.")
            return redirect(f'/cashflow/?fy={fy_str}' if fy_str else 'cashflow_dashboard')
            
        try:
            import pandas as pd
            entry_date = pd.to_datetime(date_str).date()
        except Exception:
            from django.utils import timezone
            entry_date = timezone.localdate()
            
        # Create entry
        CashFlowEntry.objects.create(
            user=target_user,
            date=entry_date,
            entry_type=entry_type,
            category=category,
            amount=amount,
            description=description
        )
        messages.success(request, f"Successfully recorded {entry_type.lower()} entry of ₹{amount:,.2f}.")
        return redirect(f'/cashflow/?fy={fy_str}' if fy_str else 'cashflow_dashboard')
        
    return redirect('cashflow_dashboard')


@login_required
def delete_cashflow_entry(request, pk):
    """Delete a manual cashflow entry."""
    target_user, is_family_view, is_consolidated = get_target_user(request)
    if is_consolidated:
        messages.error(request, "Cannot delete entries in consolidated view.")
        return redirect('cashflow_dashboard')
        
    from .models import CashFlowEntry
    entry = get_object_or_404(CashFlowEntry, pk=pk, user=target_user)
    amount = entry.amount
    category = entry.category
    entry.delete()
    
    fy_str = request.GET.get('fy', '')
    messages.success(request, f"Deleted manual entry of ₹{amount:,.2f} under {category.lower()}.")
    return redirect(f'/cashflow/?fy={fy_str}' if fy_str else 'cashflow_dashboard')


@login_required
def export_cashflow_excel(request):
    """Export cashflow data to Excel, respecting active session filters."""
    import pandas as pd
    import io
    from django.http import HttpResponse
    
    target_user, is_family_view, is_consolidated = get_target_user(request)

    # Load session filters
    session_filters = request.session.get('cashflow_filters', {})
    fy_str = request.GET.get('fy') or session_filters.get('fy')
    if not fy_str:
        from datetime import date
        today = date.today()
        y = today.year
        if today.month < 4:
            y -= 1
        fy_str = f"{y}-{y+1}"

    months = session_filters.get('months', [])
    income_types = session_filters.get('income_types', [])
    expense_categories = session_filters.get('expense_categories', [])
    investment_types = session_filters.get('investment_types', [])

    try:
        monthly_data, fy_totals = get_fy_cashflow_details(
            target_user, fy_str,
            months=months,
            income_types=income_types,
            expense_categories=expense_categories,
            investment_types=investment_types
        )
        
        # 1. Monthly DataFrame
        monthly_rows = []
        for m in monthly_data:
            monthly_rows.append({
                'Month': m['month_name'],
                'Salary (Manual)': float(m['salary']),
                'Other Income (Manual)': float(m['other_income']),
                'FD Interest (DB)': float(m['fd_interest']),
                'PF Interest (DB)': float(m['pf_interest']),
                'Other Interest (DB)': float(m['other_interest']),
                'Stock Realized Profit (DB)': float(m['stock_realized']),
                'MF Realized Profit (DB)': float(m['mf_realized']),
                'Total Income': float(m['total_income']),
                'Daily Expenses (Manual)': float(m['daily_expense']),
                'EMIs (DB)': float(m['emi']),
                'SIPs (DB)': float(m['sip']),
                'Other Expenses (Manual)': float(m['other_expense']),
                'Total Expenses': float(m['total_expenses']),
                'Net Cash Flow': float(m['net_cashflow'])
            })
        df_monthly = pd.DataFrame(monthly_rows)
        
        # 2. FY Summary DataFrame
        summary_rows = [
            {'Category': 'Total Income', 'Item': 'Salary', 'Amount': float(fy_totals['salary'])},
            {'Category': 'Total Income', 'Item': 'Other Income', 'Amount': float(fy_totals['other_income'])},
            {'Category': 'Total Income', 'Item': 'FD Interest', 'Amount': float(fy_totals['fd_interest'])},
            {'Category': 'Total Income', 'Item': 'PF Interest', 'Amount': float(fy_totals['pf_interest'])},
            {'Category': 'Total Income', 'Item': 'Other Interest', 'Amount': float(fy_totals['other_interest'])},
            {'Category': 'Total Income', 'Item': 'Stock Realized Profit', 'Amount': float(fy_totals['stock_realized'])},
            {'Category': 'Total Income', 'Item': 'MF Realized Profit', 'Amount': float(fy_totals['mf_realized'])},
            {'Category': 'Total Income', 'Item': 'TOTAL INCOME', 'Amount': float(fy_totals['total_income'])},
            {'Category': 'Total Expenses', 'Item': 'Daily Expenses', 'Amount': float(fy_totals['daily_expense'])},
            {'Category': 'Total Expenses', 'Item': 'EMIs', 'Amount': float(fy_totals['emi'])},
            {'Category': 'Total Expenses', 'Item': 'SIPs', 'Amount': float(fy_totals['sip'])},
            {'Category': 'Total Expenses', 'Item': 'Other Expenses', 'Amount': float(fy_totals['other_expense'])},
            {'Category': 'Total Expenses', 'Item': 'TOTAL EXPENSES', 'Amount': float(fy_totals['total_expenses'])},
            {'Category': 'Summary', 'Item': 'NET CASH FLOW', 'Amount': float(fy_totals['net_cashflow'])},
        ]
        df_summary = pd.DataFrame(summary_rows)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_monthly.to_excel(writer, index=False, sheet_name='Monthly CashFlow')
            df_summary.to_excel(writer, index=False, sheet_name='FY Summary')
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="cashflow_export_{fy_str}.xlsx"'
        return response
    except Exception as e:
        messages.error(request, f"Excel export failed: {e}")
        return redirect('cashflow_dashboard')


@login_required
def export_cashflow_pdf(request):
    """Export cashflow data to PDF, respecting active session filters."""
    from django.http import HttpResponse
    from datetime import date
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io
    
    target_user, is_family_view, is_consolidated = get_target_user(request)

    # Load session filters
    session_filters = request.session.get('cashflow_filters', {})
    fy_str = request.GET.get('fy') or session_filters.get('fy')
    if not fy_str:
        today = date.today()
        y = today.year
        if today.month < 4:
            y -= 1
        fy_str = f"{y}-{y+1}"

    months = session_filters.get('months', [])
    income_types = session_filters.get('income_types', [])
    expense_categories = session_filters.get('expense_categories', [])
    investment_types = session_filters.get('investment_types', [])

    try:
        monthly_data, fy_totals = get_fy_cashflow_details(
            target_user, fy_str,
            months=months,
            income_types=income_types,
            expense_categories=expense_categories,
            investment_types=investment_types
        )
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            name='TitleStyle',
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor('#003D7C'),
            alignment=1,
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            name='SubTitleStyle',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#6c757d'),
            alignment=1,
            spaceAfter=20
        )
        h2_style = ParagraphStyle(
            name='H2Style',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.HexColor('#1a1e21'),
            spaceBefore=15,
            spaceAfter=10
        )
        normal_style = ParagraphStyle(
            name='NormalStyle',
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#1a1e21')
        )
        header_cell_style = ParagraphStyle(
            name='HeaderCell',
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.white
        )
        cell_style = ParagraphStyle(
            name='Cell',
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#1a1e21')
        )
        cell_bold_style = ParagraphStyle(
            name='CellBold',
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=colors.HexColor('#1a1e21')
        )
        
        story = []
        
        story.append(Paragraph(f"FOLIUX CASH FLOW REPORT", title_style))
        story.append(Paragraph(f"Financial Year: {fy_str} | User: {target_user.username}", subtitle_style))
        
        story.append(Paragraph("Executive Summary", h2_style))
        summary_data = [
            [
                Paragraph("<b>Total Income</b>", normal_style),
                Paragraph("<b>Total Expenses</b>", normal_style),
                Paragraph("<b>Net Cash Flow</b>", normal_style)
            ],
            [
                Paragraph(f"<font color='#008D4C'><b>₹{fy_totals['total_income']:,.2f}</b></font>", title_style),
                Paragraph(f"<font color='#D62A2D'><b>₹{fy_totals['total_expenses']:,.2f}</b></font>", title_style),
                Paragraph(f"<font color=\"{'#008D4C' if fy_totals['net_cashflow'] >= 0 else '#D62A2D'}\"><b>₹{fy_totals['net_cashflow']:,.2f}</b></font>", title_style)
            ]
        ]
        summary_table = Table(summary_data, colWidths=[180, 180, 180])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f4f7f9')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e9ecef')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("Month-wise Breakdown", h2_style))
        
        table_data = [[
            Paragraph("Month", header_cell_style),
            Paragraph("Income (Man)", header_cell_style),
            Paragraph("Interest (FD/PF)", header_cell_style),
            Paragraph("Profit (Stk/MF)", header_cell_style),
            Paragraph("Total Income", header_cell_style),
            Paragraph("Expense (Man)", header_cell_style),
            Paragraph("EMIs", header_cell_style),
            Paragraph("SIPs", header_cell_style),
            Paragraph("Total Expense", header_cell_style),
            Paragraph("Net CashFlow", header_cell_style),
        ]]
        
        for m in monthly_data:
            manual_inc = m['salary'] + m['other_income']
            interest_inc = m['fd_interest'] + m['pf_interest'] + m['other_interest']
            profit_inc = m['stock_realized'] + m['mf_realized']
            manual_exp = m['daily_expense'] + m['other_expense']
            
            table_data.append([
                Paragraph(m['month_name'], cell_style),
                Paragraph(f"₹{manual_inc:,.0f}", cell_style),
                Paragraph(f"₹{interest_inc:,.0f}", cell_style),
                Paragraph(f"₹{profit_inc:,.0f}", cell_style),
                Paragraph(f"<b>₹{m['total_income']:,.0f}</b>", cell_bold_style),
                Paragraph(f"₹{manual_exp:,.0f}", cell_style),
                Paragraph(f"₹{m['emi']:,.0f}", cell_style),
                Paragraph(f"₹{m['sip']:,.0f}", cell_style),
                Paragraph(f"<b>₹{m['total_expenses']:,.0f}</b>", cell_bold_style),
                Paragraph(f"<font color=\"{'#008D4C' if m['net_cashflow'] >= 0 else '#D62A2D'}\"><b>₹{m['net_cashflow']:,.0f}</b></font>", cell_bold_style),
            ])
            
        manual_inc_tot = fy_totals['salary'] + fy_totals['other_income']
        interest_inc_tot = fy_totals['fd_interest'] + fy_totals['pf_interest'] + fy_totals['other_interest']
        profit_inc_tot = fy_totals['stock_realized'] + fy_totals['mf_realized']
        manual_exp_tot = fy_totals['daily_expense'] + fy_totals['other_expense']
        
        table_data.append([
            Paragraph("<b>TOTAL</b>", cell_bold_style),
            Paragraph(f"<b>₹{manual_inc_tot:,.0f}</b>", cell_bold_style),
            Paragraph(f"<b>₹{interest_inc_tot:,.0f}</b>", cell_bold_style),
            Paragraph(f"<b>₹{profit_inc_tot:,.0f}</b>", cell_bold_style),
            Paragraph(f"<b>₹{fy_totals['total_income']:,.0f}</b>", cell_bold_style),
            Paragraph(f"<b>₹{manual_exp_tot:,.0f}</b>", cell_bold_style),
            Paragraph(f"<b>₹{fy_totals['emi']:,.0f}</b>", cell_bold_style),
            Paragraph(f"<b>₹{fy_totals['sip']:,.0f}</b>", cell_bold_style),
            Paragraph(f"<b>₹{fy_totals['total_expenses']:,.0f}</b>", cell_bold_style),
            Paragraph(f"<font color=\"{'#008D4C' if fy_totals['net_cashflow'] >= 0 else '#D62A2D'}\"><b>₹{fy_totals['net_cashflow']:,.0f}</b></font>", cell_bold_style),
        ])
        
        cf_table = Table(table_data, colWidths=[70, 52, 52, 52, 55, 52, 45, 45, 55, 60])
        cf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003D7C')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8fafc')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(cf_table)
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="cashflow_report_{fy_str}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"PDF export failed: {e}")
        return redirect('cashflow_dashboard')


@login_required
@require_POST
def report_missing_instrument(request):
    """API endpoint to report a missing Stock/ETF/MF/NPS/Coin instrument."""
    import json
    import logging
    import threading
    from django.http import JsonResponse
    from django.core.mail import send_mail
    from django.conf import settings
    from django.utils import timezone
    from .models import MissingInstrumentRequest
    
    logger = logging.getLogger(__name__)
    
    try:
        data = json.loads(request.body)
        searched_name = data.get('name', '').strip()
        instrument_type = data.get('type', 'Stock/ETF').strip()
    except Exception:
        searched_name = request.POST.get('name', '').strip()
        instrument_type = request.POST.get('type', 'Stock/ETF').strip()
        
    if not searched_name:
        return JsonResponse({'status': 'error', 'message': 'Instrument name is required.'}, status=400)
        
    # Log the request
    logger.info(f"User {request.user.username} (ID: {request.user.id}) reported missing {instrument_type}: {searched_name}")
    
    # Store request in logs/database
    db_name = f"[{instrument_type}] {searched_name}"
    MissingInstrumentRequest.objects.create(
        user=request.user,
        searched_name=db_name
    )
    
    # Send email in background
    subject = f"[FOLIUX] Missing {instrument_type} Report: {searched_name}"
    message = (
        f"Hello Admin,\n\n"
        f"A user has reported a missing {instrument_type} in the system.\n\n"
        f"User: {request.user.username} ({request.user.email})\n"
        f"Reported Name: {searched_name}\n"
        f"Type: {instrument_type}\n"
        f"Time: {timezone.now()}\n\n"
        f"Best regards,\n"
        f"FOLIUX System"
    )
    
    def send_bg_email():
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['jitendra.kar@gmail.com'],
                fail_silently=False
            )
            logger.info(f"Email sent successfully for missing {instrument_type}: {searched_name}")
        except Exception as email_err:
            logger.error(f"Failed to send email for missing {instrument_type}: {email_err}")

    thread = threading.Thread(target=send_bg_email)
    thread.start()
    
    return JsonResponse({
        'status': 'ok',
        'message': 'Stock/ETF name has been sent to the admin for review.'
    })


@login_required
def tax_calculator_api(request):
    if request.method not in ['GET', 'POST']:
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    from decimal import Decimal
    from datetime import date
    import json
    from .tax_utils import get_tax_portfolio_data, calculate_taxes, fy_to_dates
    from .models import UserTaxProfile
    
    user = request.user
    fy = request.GET.get('fy') or request.POST.get('fy') or '2026-2027'
    
    # Get or create UserTaxProfile for the user and financial year
    profile, created = UserTaxProfile.objects.get_or_create(user=user, financial_year=fy)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Update the profile fields
            profile.salary = Decimal(str(data.get('salary', profile.salary)))
            profile.business_income = Decimal(str(data.get('business_income', profile.business_income)))
            profile.other_taxable_income = Decimal(str(data.get('other_taxable_income', profile.other_taxable_income)))
            profile.agricultural_income = Decimal(str(data.get('agricultural_income', profile.agricultural_income)))
            profile.hra_received = Decimal(str(data.get('hra_received', profile.hra_received)))
            profile.rent_paid = Decimal(str(data.get('rent_paid', profile.rent_paid)))
            profile.home_loan_interest = Decimal(str(data.get('home_loan_interest', profile.home_loan_interest)))
            profile.section_80c = Decimal(str(data.get('section_80c', profile.section_80c)))
            profile.section_80d = Decimal(str(data.get('section_80d', profile.section_80d)))
            profile.section_80ccd1b = Decimal(str(data.get('section_80ccd1b', profile.section_80ccd1b)))
            profile.section_80g = Decimal(str(data.get('section_80g', profile.section_80g)))
            profile.other_deductions = Decimal(str(data.get('other_deductions', profile.other_deductions)))
            profile.save()
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Invalid request body: {str(e)}"}, status=400)

    # 1. Fetch live portfolio data
    portfolio_data = get_tax_portfolio_data(user, fy)
    
    # 2. Merge with saved profile (declarations)
    state = {
        'salary': profile.salary,
        'business_income': profile.business_income,
        'other_taxable_income': profile.other_taxable_income,
        'agricultural_income': profile.agricultural_income,
        'hra_received': profile.hra_received,
        'rent_paid': profile.rent_paid,
        'home_loan_interest': profile.home_loan_interest,
        'section_80c': profile.section_80c,
        'section_80d': profile.section_80d,
        'section_80ccd1b': profile.section_80ccd1b,
        'section_80g': profile.section_80g,
        'other_deductions': profile.other_deductions,
        # portfolio values:
        'rental_income': portfolio_data['rental_income'],
        'fd_interest': portfolio_data['fd_interest'],
        'stock_dividends': portfolio_data['stock_dividends'],
        'mf_dividends': portfolio_data['mf_dividends'],
        'stcg_equity': portfolio_data['stcg_equity'],
        'ltcg_equity': portfolio_data['ltcg_equity'],
        'crypto_gains': portfolio_data['crypto_gains'],
        'debt_gains': portfolio_data['debt_gains'],
        'nps_contrib': portfolio_data['nps_contrib'],
        'ppf_contrib': portfolio_data['ppf_contrib'],
        'elss_contrib': portfolio_data['elss_contrib'],
    }
    
    # 3. Calculate taxes
    results = calculate_taxes(state)
    
    # 4. Fetch historical years for comparison
    historical_comparison = []
    other_profiles = UserTaxProfile.objects.filter(user=user).exclude(financial_year=fy).order_by('financial_year')
    for op in other_profiles:
        try:
            op_portfolio = get_tax_portfolio_data(user, op.financial_year)
            op_state = {
                'salary': op.salary,
                'business_income': op.business_income,
                'other_taxable_income': op.other_taxable_income,
                'agricultural_income': op.agricultural_income,
                'hra_received': op.hra_received,
                'rent_paid': op.rent_paid,
                'home_loan_interest': op.home_loan_interest,
                'section_80c': op.section_80c,
                'section_80d': op.section_80d,
                'section_80ccd1b': op.section_80ccd1b,
                'section_80g': op.section_80g,
                'other_deductions': op.other_deductions,
                'rental_income': op_portfolio['rental_income'],
                'fd_interest': op_portfolio['fd_interest'],
                'stock_dividends': op_portfolio['stock_dividends'],
                'mf_dividends': op_portfolio['mf_dividends'],
                'stcg_equity': op_portfolio['stcg_equity'],
                'ltcg_equity': op_portfolio['ltcg_equity'],
                'crypto_gains': op_portfolio['crypto_gains'],
                'debt_gains': op_portfolio['debt_gains'],
                'nps_contrib': op_portfolio['nps_contrib'],
                'ppf_contrib': op_portfolio['ppf_contrib'],
                'elss_contrib': op_portfolio['elss_contrib'],
            }
            op_res = calculate_taxes(op_state)
            historical_comparison.append({
                'fy': op.financial_year,
                'total_income': op_res['total_income'],
                'tax_old': op_res['regimes']['old']['total_tax'],
                'tax_new': op_res['regimes']['new']['total_tax'],
                'recommended': op_res['recommended_regime'],
            })
        except Exception as op_err:
            logger.error(f"Error calculating historical comparison for {op.financial_year}: {op_err}")

    # 5. Handle Projection
    projection = {}
    today = date.today()
    fy_start, fy_end = fy_to_dates(fy)
    if fy_start <= today <= fy_end:
        months_elapsed = max(1, (today.year - fy_start.year) * 12 + (today.month - fy_start.month))
        projection_factor = Decimal('12') / Decimal(str(months_elapsed))
        
        projected_salary = state['salary'] * projection_factor
        projected_business = state['business_income'] * projection_factor
        projected_dividends = (state['stock_dividends'] + state['mf_dividends']) * projection_factor
        projected_stcg = state['stcg_equity'] * projection_factor
        
        projected_state = state.copy()
        projected_state['salary'] = projected_salary
        projected_state['business_income'] = projected_business
        projected_state['stock_dividends'] = projected_dividends
        projected_state['stcg_equity'] = projected_stcg
        
        proj_res = calculate_taxes(projected_state)
        projection = {
            'months_elapsed': months_elapsed,
            'projected_salary': float(projected_salary),
            'projected_business': float(projected_business),
            'projected_stcg': float(projected_stcg),
            'tax_old': proj_res['regimes']['old']['total_tax'],
            'tax_new': proj_res['regimes']['new']['total_tax'],
            'recommended': proj_res['recommended_regime'],
        }

    return JsonResponse({
        'status': 'success',
        'saved_inputs': {
            'salary': float(profile.salary),
            'business_income': float(profile.business_income),
            'other_taxable_income': float(profile.other_taxable_income),
            'agricultural_income': float(profile.agricultural_income),
            'hra_received': float(profile.hra_received),
            'rent_paid': float(profile.rent_paid),
            'home_loan_interest': float(profile.home_loan_interest),
            'section_80c': float(profile.section_80c),
            'section_80d': float(profile.section_80d),
            'section_80ccd1b': float(profile.section_80ccd1b),
            'section_80g': float(profile.section_80g),
            'other_deductions': float(profile.other_deductions),
        },
        'portfolio_data': {
            'rental_income': float(portfolio_data['rental_income']),
            'fd_interest': float(portfolio_data['fd_interest']),
            'stock_dividends': float(portfolio_data['stock_dividends']),
            'mf_dividends': float(portfolio_data['mf_dividends']),
            'stcg_equity': float(portfolio_data['stcg_equity']),
            'ltcg_equity': float(portfolio_data['ltcg_equity']),
            'crypto_gains': float(portfolio_data['crypto_gains']),
            'debt_gains': float(portfolio_data['debt_gains']),
            'nps_contrib': float(portfolio_data['nps_contrib']),
            'ppf_contrib': float(portfolio_data['ppf_contrib']),
            'elss_contrib': float(portfolio_data['elss_contrib']),
        },
        'results': results,
        'historical_comparison': historical_comparison,
        'projection': projection,
    })


@login_required
def download_tax_report(request):
    from decimal import Decimal
    from datetime import date, timedelta
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io
    
    report_type = request.GET.get('report_type', 'summary')
    fy = request.GET.get('fy', '2026-2027')
    user = request.user

    from .tax_utils import get_tax_portfolio_data, calculate_taxes, fy_to_dates
    from .models import UserTaxProfile, Dividend, FixedAsset
    
    portfolio_data = get_tax_portfolio_data(user, fy)
    profile, _ = UserTaxProfile.objects.get_or_create(user=user, financial_year=fy)
    start_date, end_date = fy_to_dates(fy)
    
    state = {
        'salary': profile.salary,
        'business_income': profile.business_income,
        'other_taxable_income': profile.other_taxable_income,
        'agricultural_income': profile.agricultural_income,
        'hra_received': profile.hra_received,
        'rent_paid': profile.rent_paid,
        'home_loan_interest': profile.home_loan_interest,
        'section_80c': profile.section_80c,
        'section_80d': profile.section_80d,
        'section_80ccd1b': profile.section_80ccd1b,
        'section_80g': profile.section_80g,
        'other_deductions': profile.other_deductions,
        'rental_income': portfolio_data['rental_income'],
        'fd_interest': portfolio_data['fd_interest'],
        'stock_dividends': portfolio_data['stock_dividends'],
        'mf_dividends': portfolio_data['mf_dividends'],
        'stcg_equity': portfolio_data['stcg_equity'],
        'ltcg_equity': portfolio_data['ltcg_equity'],
        'crypto_gains': portfolio_data['crypto_gains'],
        'debt_gains': portfolio_data['debt_gains'],
        'nps_contrib': portfolio_data['nps_contrib'],
        'ppf_contrib': portfolio_data['ppf_contrib'],
        'elss_contrib': portfolio_data['elss_contrib'],
    }
    
    results = calculate_taxes(state)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        name='TaxTitleStyle',
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#003D7C'),
        alignment=1,
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        name='TaxSubTitleStyle',
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#6c757d'),
        alignment=1,
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        name='TaxH2Style',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#003D7C'),
        spaceBefore=12,
        spaceAfter=6
    )
    normal_style = ParagraphStyle(
        name='TaxNormalStyle',
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#1a1e21')
    )
    bold_style = ParagraphStyle(
        name='TaxBoldStyle',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#1a1e21')
    )
    header_style = ParagraphStyle(
        name='TaxHeaderStyle',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white
    )

    story = []
    
    story.append(Paragraph(f"FOLIUX TAX STUDIO REPORT", title_style))
    story.append(Paragraph(f"Taxpayer: {user.username} | Financial Year: {fy} | Generated: {date.today().strftime('%B %d, %Y')}", subtitle_style))
    story.append(Spacer(1, 10))

    def build_summary_section(story_list):
        story_list.append(Paragraph("TAX SUMMARY & REGIME COMPARISON", h2_style))
        story_list.append(Paragraph("A comparative analysis of your income tax liability under the Old and New regimes.", normal_style))
        story_list.append(Spacer(1, 10))
        
        old = results['regimes']['old']
        new = results['regimes']['new']
        
        data = [
            [Paragraph("Tax Parameter", header_style), Paragraph("Old Tax Regime (INR)", header_style), Paragraph("New Tax Regime (INR)", header_style)],
            [Paragraph("Gross Salary", normal_style), f"{(profile.salary or Decimal('0')):,.2f}", f"{(profile.salary or Decimal('0')):,.2f}"],
            [Paragraph("Business & Other Income", normal_style), f"{((profile.business_income or Decimal('0')) + (profile.other_taxable_income or Decimal('0'))):,.2f}", f"{((profile.business_income or Decimal('0')) + (profile.other_taxable_income or Decimal('0'))):,.2f}"],
            [Paragraph("Rental & Interest Income", normal_style), f"{(state['rental_income'] + state['fd_interest']):,.2f}", f"{(state['rental_income'] + state['fd_interest']):,.2f}"],
            [Paragraph("Dividends & Debt Gains", normal_style), f"{(state['stock_dividends'] + state['mf_dividends'] + state['debt_gains']):,.2f}", f"{(state['stock_dividends'] + state['mf_dividends'] + state['debt_gains']):,.2f}"],
            [Paragraph("Total Deductions & Exemptions", normal_style), f"{old['deductions']:,.2f}", f"{new['deductions']:,.2f}"],
            [Paragraph("Net Taxable Income", normal_style), f"{old['taxable_income']:,.2f}", f"{new['taxable_income']:,.2f}"],
            [Paragraph("Tax on Normal Income", normal_style), f"{old['tax_on_normal']:,.2f}", f"{new['tax_on_normal']:,.2f}"],
            [Paragraph("Tax on Capital Gains (Equity)", normal_style), f"{(old['tax_on_stcg'] + old['tax_on_ltcg']):,.2f}", f"{(new['tax_on_stcg'] + new['tax_on_ltcg']):,.2f}"],
            [Paragraph("Tax on Crypto (Section 115BBH)", normal_style), f"{old['tax_on_crypto']:,.2f}", f"{new['tax_on_crypto']:,.2f}"],
            [Paragraph("Rebate u/s 87A", normal_style), f"{old['rebate']:,.2f}", f"{new['rebate']:,.2f}"],
            [Paragraph("Surcharge", normal_style), f"{old['surcharge']:,.2f}", f"{new['surcharge']:,.2f}"],
            [Paragraph("Health & Education Cess (4%)", normal_style), f"{old['cess']:,.2f}", f"{new['cess']:,.2f}"],
            [Paragraph("Total Tax Payable", bold_style), Paragraph(f"<b>{old['total_tax']:,.2f}</b>", bold_style), Paragraph(f"<b>{new['total_tax']:,.2f}</b>", bold_style)],
        ]
        
        t = Table(data, colWidths=[200, 160, 160])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003D7C')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8f9fa')]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e9ecef')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story_list.append(t)
        story_list.append(Spacer(1, 15))
        
        rec = results['recommended_regime']
        saved = results['tax_saved']
        story_list.append(Paragraph(f"<b>RECOMMENDATION</b>: We recommend the <b>{rec} Tax Regime</b> for you as it results in a lower tax liability. You save <b>INR {saved:,.2f}</b> under this regime.", bold_style))
        story_list.append(Spacer(1, 15))

    def build_capital_gains_section(story_list):
        story_list.append(Paragraph("CAPITAL GAINS TAX DETAILS", h2_style))
        story_list.append(Paragraph("Realized Capital Gains from Stocks, Mutual Funds, and Cryptocurrency assets during the financial year.", normal_style))
        story_list.append(Spacer(1, 10))
        
        data = [
            [Paragraph("Asset Category", header_style), Paragraph("Realized Gains (INR)", header_style), Paragraph("Holding Period", header_style), Paragraph("Tax Rate", header_style), Paragraph("Tax Amount (INR)", header_style)],
            [Paragraph("Equity Stocks & MFs (Short-Term u/s 111A)", normal_style), f"{state['stcg_equity']:,.2f}", "<= 1 Year", "20.0%", f"{results['regimes']['new']['tax_on_stcg']:,.2f}"],
            [Paragraph("Equity Stocks & MFs (Long-Term u/s 112A)", normal_style), f"{state['ltcg_equity']:,.2f}", "> 1 Year", "12.5% (above 1.25L)", f"{results['regimes']['new']['tax_on_ltcg']:,.2f}"],
            [Paragraph("Debt Mutual Funds (Slabs)", normal_style), f"{state['debt_gains']:,.2f}", "Any", "Slab Rate", "Taxed at Slab"],
            [Paragraph("Cryptocurrency / Coins (Section 115BBH)", normal_style), f"{state['crypto_gains']:,.2f}", "Any", "30.0%", f"{results['regimes']['new']['tax_on_crypto']:,.2f}"],
        ]
        
        t = Table(data, colWidths=[180, 110, 80, 80, 90])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003D7C')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story_list.append(t)
        story_list.append(Spacer(1, 15))

    def build_dividends_section(story_list):
        story_list.append(Paragraph("DIVIDEND INCOME DETAILS", h2_style))
        story_list.append(Paragraph("Dividends received from stocks and mutual funds during the financial year.", normal_style))
        story_list.append(Spacer(1, 10))
        
        dividends_list = Dividend.objects.filter(user=user, received_date__range=(start_date, end_date)).order_by('received_date')
        
        if dividends_list.exists():
            data = [[Paragraph("Received Date", header_style), Paragraph("Instrument", header_style), Paragraph("Amount (INR)", header_style)]]
            for d_rec in dividends_list:
                data.append([d_rec.received_date.strftime('%d-%b-%Y'), d_rec.instrument.symbol, f"{d_rec.amount:,.2f}"])
            
            data.append([Paragraph("<b>Total Dividends</b>", bold_style), "", Paragraph(f"<b>{state['stock_dividends']:,.2f}</b>", bold_style)])
            
            t = Table(data, colWidths=[150, 220, 150])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003D7C')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8f9fa')]),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e9ecef')),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story_list.append(t)
        else:
            story_list.append(Paragraph("No stock dividend transaction records found in the portfolio for this financial year.", normal_style))
        story_list.append(Spacer(1, 15))

    def build_interest_section(story_list):
        story_list.append(Paragraph("INTEREST INCOME DETAILS", h2_style))
        story_list.append(Paragraph("Interest income earned or accrued from Fixed Deposits and Recurring Deposits during the financial year.", normal_style))
        story_list.append(Spacer(1, 10))
        
        fds = FixedAsset.objects.filter(user=user, asset_type__in=['FD', 'RD'], investment_date__lte=end_date)
        if fds.exists():
            data = [[Paragraph("Instrument Name", header_style), Paragraph("Asset Type", header_style), Paragraph("Principal (INR)", header_style), Paragraph("Interest Rate", header_style), Paragraph("Interest Accrued (INR)", header_style)]]
            tot_int = Decimal('0')
            for fd in fds:
                val_end = fd.value_at_date(end_date)
                if fd.investment_date >= start_date:
                    val_start = fd.invested_amount_decimal
                else:
                    val_start = fd.value_at_date(start_date - timedelta(days=1))
                interest = val_end - val_start
                if fd.asset_type == 'RD' and fd.investment_date < start_date:
                    dep_start = max(start_date, fd.investment_date)
                    dep_end = min(end_date, fd.maturity_date) if fd.maturity_date else end_date
                    if dep_end >= dep_start:
                        months = (dep_end.year - dep_start.year) * 12 + (dep_end.month - dep_start.month) + 1
                        interest -= (fd.monthly_deposit or Decimal('0')) * months
                interest = max(Decimal('0'), interest)
                tot_int += interest
                
                data.append([
                    fd.instrument_name,
                    fd.get_asset_type_display(),
                    f"{fd.invested_amount_decimal:,.2f}",
                    f"{fd.interest_rate_decimal:.2f}%",
                    f"{interest:,.2f}"
                ])
            data.append([Paragraph("<b>Total FD/RD Interest</b>", bold_style), "", "", "", Paragraph(f"<b>{tot_int:,.2f}</b>", bold_style)])
            t = Table(data, colWidths=[160, 90, 100, 70, 100])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003D7C')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e9ecef')),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8f9fa')]),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e9ecef')),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story_list.append(t)
        else:
            story_list.append(Paragraph("No FD/RD interest assets found in the portfolio for this financial year.", normal_style))
        story_list.append(Spacer(1, 15))

    if report_type == 'summary':
        build_summary_section(story)
    elif report_type == 'capital_gains':
        build_capital_gains_section(story)
    elif report_type == 'dividends':
        build_dividends_section(story)
    elif report_type == 'interest':
        build_interest_section(story)
    elif report_type == 'statement':
        build_summary_section(story)
        story.append(PageBreak())
        build_capital_gains_section(story)
        story.append(Spacer(1, 10))
        build_interest_section(story)
        story.append(PageBreak())
        build_dividends_section(story)
    else:
        return HttpResponse("Invalid report type.", status=400)

    doc.build(story)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="foliux_tax_{report_type}_{fy}.pdf"'
    return response


# =========================================================================
# CALCULATOR SAVE & MANAGEMENT API VIEWS
# =========================================================================
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import models
from .models import SavedCalculation
import json

@csrf_exempt
@require_http_methods(["POST"])
def ajax_login_api(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return JsonResponse({'status': 'error', 'message': 'Username and password are required'}, status=400)
        
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'status': 'success', 'message': 'Authenticated successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid username/email or password'}, status=401)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def save_calculation_api(request):
    try:
        data = json.loads(request.body)
        calc_id = data.get('id') # Optional, if updating an existing one
        calc_type = data.get('calc_type')
        calc_name = data.get('calc_name')
        name = data.get('name')
        input_values = data.get('input_values', {})
        calculated_results = data.get('calculated_results', {})
        is_favorite = data.get('is_favorite', False)

        if not calc_type or not calc_name or not name:
            return JsonResponse({'status': 'error', 'message': 'Calculator type, calculator name, and custom name are required'}, status=400)

        if calc_id:
            try:
                calc = SavedCalculation.objects.get(id=calc_id, user=request.user)
                calc.calc_type = calc_type
                calc.calc_name = calc_name
                calc.name = name
                calc.input_values = input_values
                calc.calculated_results = calculated_results
                calc.is_favorite = is_favorite
                calc.save()
            except SavedCalculation.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Saved calculation not found'}, status=404)
        else:
            calc = SavedCalculation.objects.create(
                user=request.user,
                calc_type=calc_type,
                calc_name=calc_name,
                name=name,
                input_values=input_values,
                calculated_results=calculated_results,
                is_favorite=is_favorite
            )
            calc_id = calc.id

        return JsonResponse({
            'status': 'success',
            'message': 'Calculation saved successfully',
            'id': calc_id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def saved_calculations_list_api(request):
    try:
        query = request.GET.get('q', '').strip().lower()
        calcs = SavedCalculation.objects.filter(user=request.user)
        
        if query:
            # Simple keyword search inside custom name, calculator name, or calculator type
            calcs = calcs.filter(
                models.Q(name__icontains=query) |
                models.Q(calc_name__icontains=query) |
                models.Q(calc_type__icontains=query)
            )

        results = []
        for c in calcs:
            results.append({
                'id': c.id,
                'calc_type': c.calc_type,
                'calc_name': c.calc_name,
                'name': c.name,
                'input_values': c.input_values,
                'calculated_results': c.calculated_results,
                'is_favorite': c.is_favorite,
                'created_at': c.created_at.strftime('%d-%m-%Y %H:%M'),
                'updated_at': c.updated_at.strftime('%d-%m-%Y %H:%M')
            })

        return JsonResponse({
            'status': 'success',
            'data': results,
            'total_count': len(results)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def delete_calculation_api(request, pk):
    try:
        calc = SavedCalculation.objects.get(id=pk, user=request.user)
        calc.delete()
        return JsonResponse({'status': 'success', 'message': 'Calculation deleted successfully'})
    except SavedCalculation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Calculation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def toggle_favorite_calculation_api(request, pk):
    try:
        calc = SavedCalculation.objects.get(id=pk, user=request.user)
        calc.is_favorite = not calc.is_favorite
        calc.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Calculation updated successfully',
            'is_favorite': calc.is_favorite
        })
    except SavedCalculation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Calculation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def duplicate_calculation_api(request, pk):
    try:
        calc = SavedCalculation.objects.get(id=pk, user=request.user)
        # Duplicate by setting pk = None and updating the name
        calc.pk = None
        calc.name = f"{calc.name} (Copy)"
        calc.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Calculation duplicated successfully',
            'id': calc.id
        })
    except SavedCalculation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Calculation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def serve_dr(request, path=''):
    """
    Serves static files from the 'dr' directory.
    If the path is empty or a directory, it defaults to 'index.html'.
    Prevents directory traversal attacks by validating the path.
    """
    import os
    from django.http import FileResponse, Http404
    from django.conf import settings
    
    dr_dir = os.path.join(settings.BASE_DIR, 'dr')
    
    # Default to index.html for empty path or directory paths
    if not path or path.endswith('/'):
        path = os.path.join(path, 'index.html')
        
    full_path = os.path.join(dr_dir, path)
    
    # Normalize and verify that the target file is inside the 'dr' directory
    normalized_path = os.path.abspath(full_path)
    if not normalized_path.startswith(os.path.abspath(dr_dir)):
        raise Http404("File not found")
        
    if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
        return FileResponse(open(normalized_path, 'rb'))
    else:
        raise Http404("File not found")


def serve_ca(request, path=''):
    """
    Serves static files from the 'ca' directory.
    If the path is empty or a directory, it defaults to 'index.html'.
    Prevents directory traversal attacks by validating the path.
    """
    import os
    from django.http import FileResponse, Http404
    from django.conf import settings
    
    ca_dir = os.path.join(settings.BASE_DIR, 'ca')
    
    # Default to index.html for empty path or directory paths
    if not path or path.endswith('/'):
        path = os.path.join(path, 'index.html')
        
    full_path = os.path.join(ca_dir, path)
    
    # Normalize and verify that the target file is inside the 'ca' directory
    normalized_path = os.path.abspath(full_path)
    if not normalized_path.startswith(os.path.abspath(ca_dir)):
        raise Http404("File not found")
        
    if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
        return FileResponse(open(normalized_path, 'rb'))
    else:
        raise Http404("File not found")


# ==========================================
# BHARAT CHICKEN POINT (BCP) MODULE
# ==========================================

BCP_MENU = [
    {
        'id': 'fresh_chicken',
        'name': 'Fresh Chicken (Whole Cut)',
        'nameHi': 'ताजा चिकन (साबुत कट)',
        'category': 'raw',
        'price': 220,
        'unit': 'Per Kg',
        'description': 'Clean, fresh whole chicken cut to your preference (curry cut, biryani cut, etc.).',
        'descriptionHi': 'आपकी पसंद के अनुसार काटा गया ताजा चिकन (करी कट, बिरयानी कट, आदि)।',
        'image': 'assets/fresh_chicken.jpg'
    },
    {
        'id': 'breast_boneless',
        'name': 'Breast Boneless Chicken',
        'nameHi': 'ब्रेस्ट बोनलेस चिकन',
        'category': 'raw',
        'price': 260,
        'unit': 'Per Kg',
        'description': 'Fresh, skinless, boneless chicken breast meat. Extremely lean and tender.',
        'descriptionHi': 'ताजा, बिना त्वचा और बिना हड्डी वाला चिकन ब्रेस्ट मीट। बहुत ही हल्का और कोमल।',
        'image': 'assets/breast_boneless.jpg'
    },
    {
        'id': 'thai_boneless',
        'name': 'Thai Boneless Chicken',
        'nameHi': 'थाई बोनलेस चिकन',
        'category': 'raw',
        'price': 320,
        'unit': 'Per Kg',
        'description': 'Juicy, boneless chicken thigh pieces, perfect for grilling, frying, or tikka.',
        'descriptionHi': 'चिकन जांघ के रसीले टुकड़े, तंदूरी, फ्राइंग या तिक्का बनाने के लिए एकदम सही।',
        'image': 'assets/thai_boneless.jpg'
    },
    {
        'id': 'chicken_tangri',
        'name': 'Chicken Tangri (Drumsticks)',
        'nameHi': 'चिकन टांगड़ी (लेग पीस)',
        'category': 'raw',
        'price': 260,
        'unit': 'Per Kg',
        'description': 'Cleaned chicken drumsticks, ready for marination and tandoori cooking.',
        'descriptionHi': 'साफ की हुई चिकन टांगड़ी (ड्रमस्टिक्स), मैरीनेशन और तंदूरी कुकिंग के लिए तैयार।',
        'image': 'assets/chicken_tangri.jpg'
    },
    {
        'id': 'chicken_wings',
        'name': 'Chicken Wings',
        'nameHi': 'चिकन विंग्स (पंख)',
        'category': 'raw',
        'price': 260,
        'unit': 'Per Kg',
        'description': 'Clean chicken wings, ideal for spicy wings fry or barbecue.',
        'descriptionHi': 'साफ चिकन विंग्स, मसालेदार विंग्स फ्राई या बारबेक्यू के लिए एकदम सही।',
        'image': 'assets/chicken_wings.jpg'
    },
    {
        'id': 'chicken_keema',
        'name': 'Chicken Keema (Minced)',
        'nameHi': 'चिकन कीमा',
        'category': 'raw',
        'price': 260,
        'unit': 'Per Kg',
        'description': 'Premium quality minced chicken, freshly prepared, low-fat.',
        'descriptionHi': 'प्रीमियम गुणवत्ता वाला कीमा चिकन, ताजा तैयार किया हुआ और कम वसा वाला।',
        'image': 'assets/chicken_keema.jpg'
    },
    {
        'id': 'chicken_full_leg',
        'name': 'Chicken Full Leg Quarter',
        'nameHi': 'चिकन फुल लेग क्वार्टर',
        'category': 'raw',
        'price': 280,
        'unit': 'Per Kg',
        'description': 'Full leg quarters containing both the thigh and the drumstick.',
        'descriptionHi': 'साबुत चिकन लेग पीस जिसमें जांघ और टांग दोनों भाग शामिल हैं।',
        'image': 'assets/chicken_full_leg.jpg'
    },
    {
        'id': 'fresh_mutton',
        'name': 'Fresh Mutton (Goat Meat)',
        'nameHi': 'ताजा मटन (बकरे का मीट)',
        'category': 'raw',
        'price': 700,
        'unit': 'Per Kg',
        'description': 'Premium, tender fresh goat meat. Sourced daily and hygienically cut.',
        'descriptionHi': 'प्रीमियम और कोमल बकरे का मीट, रोजाना ताजा और स्वच्छता से कटा हुआ।',
        'image': 'assets/fresh_mutton.jpg'
    },
    {
        'id': 'mutton_kabab',
        'name': 'Mutton Seekh Kabab',
        'nameHi': 'मटन सीख कबाब',
        'category': 'ready',
        'price': 350,
        'unit': 'Per Pkt',
        'description': 'Authentic spiced minced mutton skewers, ready to grill, pan-fry, or eat.',
        'descriptionHi': 'स्वादिष्ट मसालेदार पिसा हुआ मटन कबाब सीक, तलने या ग्रिल करने के लिए तैयार।',
        'image': 'assets/mutton_kabab.jpg'
    },
    {
        'id': 'chicken_salami',
        'name': 'Chicken Salami',
        'nameHi': 'चिकन सलामी',
        'category': 'ready',
        'price': 180,
        'unit': 'Per Pkt',
        'description': 'Deliciously sliced chicken cold-cut salami, mildly seasoned.',
        'descriptionHi': 'स्वादिष्ट कटी हुई चिकन सलामी, हल्के मसालों के साथ सीजन की हुई।',
        'image': 'assets/chicken_salami.jpg'
    },
    {
        'id': 'spicy_salami',
        'name': 'Spicy Chicken Salami',
        'nameHi': 'तीखी चिकन सलामी',
        'category': 'ready',
        'price': 180,
        'unit': 'Per Pkt',
        'description': 'Sliced chicken salami loaded with red chili flakes and spices.',
        'descriptionHi': 'लाल मिर्च के फ्लेक्स और तीखे मसालों से भरपूर चिकन सलामी स्लाइस।',
        'image': 'assets/spicy_salami.jpg'
    },
    {
        'id': 'chicken_nuggets',
        'name': 'Chicken Nuggets',
        'nameHi': 'चिकन नगेट्स',
        'category': 'ready',
        'price': 250,
        'unit': 'Per Pkt',
        'description': 'Golden, crispy, breaded chicken nuggets. Store and fry as needed.',
        'descriptionHi': 'सुनहरे, कुरकुरे और ब्रेड क्रम्ब्स वाले चिकन नगेट्स। घर पर तलने के लिए तैयार।',
        'image': 'assets/chicken_nuggets.jpg'
    },
    {
        'id': 'angara_kabab',
        'name': 'Angara Chicken Kabab',
        'nameHi': 'अंगारा चिकन कबाब',
        'category': 'ready',
        'price': 250,
        'unit': 'Per Pkt',
        'description': 'Spicy chicken seekh kababs marinated in fiery red Angara spices.',
        'descriptionHi': 'तीखे लाल अंगारा मसालों में मैरीनेट किया हुआ चिकन सीख कबाब।',
        'image': 'assets/angara_kabab.jpg'
    },
    {
        'id': 'mughlai_kabab',
        'name': 'Mughlai Chicken Kabab',
        'nameHi': 'मुगलई चिकन कबाब',
        'category': 'ready',
        'price': 250,
        'unit': 'Per Pkt',
        'description': 'Creamy, rich, and mildly flavored chicken seekh kababs in royal Mughlai marinade.',
        'descriptionHi': 'शाही मलाईदार और बेहद कोमल मुगलई मैरीनेशन से तैयार चिकन सीख कबाब।',
        'image': 'assets/mughlai_kabab.jpg'
    },
    {
        'id': 'peri_peri_kabab',
        'name': 'Peri-Peri Chicken Kabab',
        'nameHi': 'पेरी-पेरी चिकन कबाब',
        'category': 'ready',
        'price': 250,
        'unit': 'Per Pkt',
        'description': 'Zesty and tangy chicken kababs marinated in citrusy African Peri-Peri sauce.',
        'descriptionHi': 'चटपटे और तीखे अफ्रीकी पेरी-पेरी सॉस से मैरीनेट किया हुआ चिकन कबाब।',
        'image': 'assets/peri_peri_kabab.jpg'
    },
    {
        'id': 'malai_kabab',
        'name': 'Malai Chicken Kabab',
        'nameHi': 'मलाई चिकन कबाब',
        'category': 'ready',
        'price': 250,
        'unit': 'Per Pkt',
        'description': 'Extremely soft, melt-in-the-mouth chicken kababs with rich cream and cheese.',
        'descriptionHi': 'अत्यंत कोमल, मुंह में घुलने वाले मलाईदार और चीजी चिकन कबाब।',
        'image': 'assets/malai_kabab.jpg'
    },
    {
        'id': 'achari_kabab',
        'name': 'Achari Chicken Kabab',
        'nameHi': 'अचारी चिकन कबाब',
        'category': 'ready',
        'price': 250,
        'unit': 'Per Pkt',
        'description': 'Tender chicken kababs with the tangy, savory flavors of traditional Indian pickle.',
        'descriptionHi': 'चिकन कबाब जिसमें भारतीय मसालों और खट्टे अचार का चटपटा स्वाद है।',
        'image': 'assets/achari_kabab.jpg'
    },
    {
        'id': 'cheesy_onion_kabab',
        'name': 'Cheesy Onion Chicken Kabab',
        'nameHi': 'चीजी अनियन चिकन कबाब',
        'category': 'ready',
        'price': 250,
        'unit': 'Per Pkt',
        'description': 'Succulent chicken kababs stuffed with mozzarella cheese and sweet onions.',
        'descriptionHi': 'मोज़ेरेला चीज़ और मीठे प्याज के टुकड़ों से भरा रसीला चिकन कबाब।',
        'image': 'assets/cheesy_onion_kabab.jpg'
    },
    {
        'id': 'karachi_chicken',
        'name': 'Karachi Chicken Fry',
        'nameHi': 'कराची चिकन फ्राई',
        'category': 'specials',
        'price': 100,
        'unit': '250 Grams',
        'description': 'Karachi-style stir fried chicken, cooked with freshly ground whole spices.',
        'descriptionHi': 'कराची स्टाइल स्वादिष्ट चिकन फ्राई, ताज़ा पीसे खड़े मसालों के साथ भुना हुआ।',
        'image': 'assets/karachi_chicken.jpg'
    },
    {
        'id': 'chicken_lollypop',
        'name': 'Chicken Lollypop Fry',
        'nameHi': 'चिकन लॉलीपॉप फ्राई',
        'category': 'specials',
        'price': 80,
        'unit': '250 Grams',
        'description': 'Indo-Chinese style crispy fried chicken drumettes coated in seasoned batter.',
        'descriptionHi': 'मसालेदार घोल में लपेटकर गहरा तला हुआ क्रिस्पी इंडो-चाइनीज चिकन विंग्स।',
        'image': 'assets/chicken_lollypop.jpg'
    },
    {
        'id': 'chicken_fry',
        'name': 'Bharat Special Chicken Fry',
        'nameHi': 'भारत स्पेशल चिकन फ्राई',
        'category': 'specials',
        'price': 200,
        'unit': 'Full Plate',
        'description': 'Our signature crispy, deep-fried chicken marinated in secret traditional spices.',
        'descriptionHi': 'हमारा विशेष क्रिस्पी फ्राइड चिकन, पारंपरिक और अनोखे मसालों से मैरीनेटेड।',
        'image': 'assets/chicken_fry.jpg'
    }
]

def bcp_read_db(file_name):
    import os
    import json
    from django.conf import settings
    file_path = os.path.join(settings.BASE_DIR, 'bcp', file_name)
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {file_name}: {e}")
        return []

def bcp_write_db(file_name, data):
    import os
    import json
    from django.conf import settings
    file_path = os.path.join(settings.BASE_DIR, 'bcp', file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing {file_name}: {e}")
        return False

def bcp_read_env():
    import os
    from django.conf import settings
    env_path = os.path.join(settings.BASE_DIR, 'bcp', '.env')
    config = {
        'IS_SMTP_ENABLED': 'false',
        'SMTP_HOST': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SMTP_USER': '',
        'SMTP_PASS': '',
        'VENDOR_EMAIL': 'sarfarajguddu.bcp@gmail.com',
        'UPI_ID': '9899946076@okbizaxis',
        'MERCHANT_NAME': 'Bharat Chicken Point'
    }
    if not os.path.exists(env_path):
        return config
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                parts = line.split('=', 1)
                k = parts[0].strip()
                v = parts[1].strip()
                config[k] = v
    except Exception as e:
        print(f"Error reading BCP .env: {e}")
    return config

def bcp_write_env(config_dict):
    import os
    from django.conf import settings
    env_path = os.path.join(settings.BASE_DIR, 'bcp', '.env')
    lines = []
    written_keys = set()
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    parts = stripped.split('=', 1)
                    k = parts[0].strip()
                    if k in config_dict:
                        lines.append(f"{k}={config_dict[k]}\n")
                        written_keys.add(k)
                        continue
                lines.append(line)
    for k, v in config_dict.items():
        if k not in written_keys:
            lines.append(f"{k}={v}\n")
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error writing BCP .env: {e}")
        return False

def bcp_get_customer_email_template(order):
    items_list = ""
    for item in order['items']:
        items_list += f"""
        <tr>
          <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item['name']}</td>
          <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{item['quantity']}</td>
          <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹{item['price']}</td>
          <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹{item['price'] * item['quantity']}</td>
        </tr>
        """
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
      <div style="background-color: #c8102e; padding: 15px; text-align: center; border-radius: 6px 6px 0 0;">
        <h2 style="color: white; margin: 0;">Bharat Chicken & Mutton Shop</h2>
      </div>
      <div style="padding: 20px;">
        <h3 style="color: #333;">Order Confirmed!</h3>
        <p>Dear <strong>{order['customerName']}</strong>,</p>
        <p>Thank you for placing your order with us. We have received your payment and our kitchen is preparing your items.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
          <thead>
            <tr style="background-color: #f8f8f8;">
              <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Item</th>
              <th style="padding: 8px; text-align: center; border-bottom: 2px solid #ddd;">Qty</th>
              <th style="padding: 8px; text-align: right; border-bottom: 2px solid #ddd;">Price</th>
              <th style="padding: 8px; text-align: right; border-bottom: 2px solid #ddd;">Total</th>
            </tr>
          </thead>
          <tbody>
            {items_list}
            <tr>
              <td colspan="3" style="padding: 8px; text-align: right; font-weight: bold;">Grand Total:</td>
              <td style="padding: 8px; text-align: right; font-weight: bold; color: #c8102e;">₹{order['totalAmount']}</td>
            </tr>
          </tbody>
        </table>

        <div style="background-color: #fff9e6; border-left: 4px solid #ffc72c; padding: 12px; margin: 20px 0;">
          <h4 style="margin: 0 0 5px 0; color: #7a5f00;">Delivery Details:</h4>
          <p style="margin: 0; font-size: 14px;"><strong>Address:</strong> {order['deliveryAddress']}</p>
          <p style="margin: 5px 0 0 0; font-size: 14px;"><strong>Phone:</strong> {order['customerPhone']}</p>
        </div>

        <p style="font-size: 14px; color: #666;">If you have any questions, feel free to call us at <strong>9899946076</strong> or <strong>9560569646</strong>.</p>
        <p style="margin-top: 30px; font-size: 12px; text-align: center; color: #999;">S-10, Private Colony, Sriniwaspuri, New Delhi - 110065</p>
      </div>
    </div>
    """

def bcp_get_vendor_email_template(order):
    items_list = ""
    for item in order['items']:
        items_list += f"""
        <tr>
          <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item['name']}</td>
          <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{item['quantity']}</td>
          <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹{item['price']}</td>
          <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹{item['price'] * item['quantity']}</td>
        </tr>
        """
    import datetime
    paid_at_dt = order['paymentDetails']['paidAt'] if order.get('paymentDetails') else order['createdAt']
    try:
        dt = datetime.datetime.fromisoformat(paid_at_dt.replace('Z', '+00:00'))
        from datetime import timezone, timedelta
        dt_ist = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
        time_str = dt_ist.strftime('%d/%m/%Y, %I:%M:%S %p')
    except Exception:
        time_str = paid_at_dt

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px; border-top: 5px solid #ffc72c;">
      <div style="background-color: #1a1a1a; padding: 15px; text-align: center; border-radius: 6px 6px 0 0;">
        <h2 style="color: #ffc72c; margin: 0;">NEW ORDER RECEIVED!</h2>
        <span style="color: #fff; font-size: 12px;">Order ID: {order['id']}</span>
      </div>
      <div style="padding: 20px;">
        <h3 style="color: #c8102e; border-bottom: 1px solid #eee; padding-bottom: 8px;">Order Details</h3>
        <p><strong>Customer:</strong> {order['customerName']}</p>
        <p><strong>Phone:</strong> <a href="tel:{order['customerPhone']}">{order['customerPhone']}</a></p>
        <p><strong>Email:</strong> {order['customerEmail']}</p>
        <p><strong>Address:</strong> {order['deliveryAddress']}</p>
        <p><strong>Time:</strong> {time_str}</p>

        <h3 style="color: #c8102e; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-top: 20px;">Items Ordered</h3>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="background-color: #f8f8f8;">
              <th style="padding: 8px; text-align: left;">Item</th>
              <th style="padding: 8px; text-align: center;">Qty</th>
              <th style="padding: 8px; text-align: right;">Price</th>
              <th style="padding: 8px; text-align: right;">Total</th>
            </tr>
          </thead>
          <tbody>
            {items_list}
            <tr style="font-weight: bold;">
              <td colspan="3" style="padding: 8px; text-align: right;">Total Amount Paid:</td>
              <td style="padding: 8px; text-align: right; color: #c8102e;">₹{order['totalAmount']}</td>
            </tr>
          </tbody>
        </table>

        <div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 12px; margin-top: 20px; border-radius: 4px;">
          <h4 style="margin: 0 0 5px 0; color: #2e7d32;">Payment Details (UPI):</h4>
          <p style="margin: 0; font-size: 14px;"><strong>Status:</strong> Success (PAID)</p>
          <p style="margin: 3px 0 0 0; font-size: 14px;"><strong>Payment Method:</strong> {order.get('paymentDetails', {}).get('method', 'UPI') if order.get('paymentDetails') else 'UPI'}</p>
          <p style="margin: 3px 0 0 0; font-size: 14px;"><strong>Transaction UTR/Reference:</strong> {order.get('paymentDetails', {}).get('utr', 'N/A') if order.get('paymentDetails') else 'N/A'}</p>
        </div>

        <div style="margin-top: 30px; text-align: center;">
          <a href="http://localhost:3000/#admin" style="background-color: #c8102e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">Open Vendor Dashboard</a>
        </div>
      </div>
    </div>
    """

def bcp_send_notification_email(to, subject, html_body, email_type):
    import random
    config = bcp_read_env()
    is_smtp_enabled = config.get('IS_SMTP_ENABLED', 'false') == 'true'
    
    if is_smtp_enabled:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            host = config.get('SMTP_HOST', 'smtp.gmail.com')
            port = int(config.get('SMTP_PORT', '587'))
            user = config.get('SMTP_USER', '')
            passwd = config.get('SMTP_PASS', '')
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'"Bharat Chicken Point" <{user}>'
            msg['To'] = to
            
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
            
            server = smtplib.SMTP(host, port)
            if port == 587:
                server.starttls()
            if user and passwd:
                server.login(user, passwd)
            server.sendmail(user, to, msg.as_string())
            server.quit()
            print(f"Real email sent successfully to {to} ({email_type})")
            
            logs = bcp_read_db('email_logs.json')
            import datetime
            logs.insert(0, {
                'id': 'L-' + str(random.randint(100000, 999999)),
                'to': to,
                'subject': subject,
                'body': html_body,
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                'mode': 'Real SMTP'
            })
            bcp_write_db('email_logs.json', logs)
            return True
        except Exception as e:
            print(f"Failed to send real email to {to}: {e}")
            
    logs = bcp_read_db('email_logs.json')
    import datetime
    logs.insert(0, {
        'id': 'L-' + str(random.randint(100000, 999999)),
        'to': to,
        'subject': subject,
        'body': html_body,
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'mode': 'Simulated Log'
    })
    bcp_write_db('email_logs.json', logs)
    print(f"[SIMULATED EMAIL LOGGED] To: {to} | Subject: {subject}")
    return True

def serve_bcp(request, path=''):
    """
    Serves static files from the 'bcp/public' directory.
    If the path is empty or a directory, it defaults to 'index.html'.
    Prevents directory traversal attacks by validating the path.
    """
    import os
    from django.http import FileResponse, Http404, HttpResponseRedirect
    from django.conf import settings
    
    if request.path == '/bcp':
        return HttpResponseRedirect('/bcp/')
        
    bcp_dir = os.path.join(settings.BASE_DIR, 'bcp', 'public')
    
    if not path or path.endswith('/'):
        path = os.path.join(path, 'index.html')
        
    full_path = os.path.join(bcp_dir, path)
    
    normalized_path = os.path.abspath(full_path)
    if not normalized_path.startswith(os.path.abspath(bcp_dir)):
        raise Http404("File not found")
        
    if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
        return FileResponse(open(normalized_path, 'rb'))
    else:
        raise Http404("File not found")

def serve_coaching(request, path=''):
    """
    Serves static files from the 'coaching' directory.
    If the path is empty or a directory, it defaults to 'index.html'.
    Prevents directory traversal attacks by validating the path.
    """
    import os
    from django.http import FileResponse, Http404, HttpResponseRedirect
    from django.conf import settings
    
    if request.path == '/coaching':
        return HttpResponseRedirect('/coaching/')
        
    coaching_dir = os.path.join(settings.BASE_DIR, 'coaching')
    
    if not path or path.endswith('/'):
        path = os.path.join(path, 'index.html')
        
    full_path = os.path.join(coaching_dir, path)
    
    normalized_path = os.path.abspath(full_path)
    if not normalized_path.startswith(os.path.abspath(coaching_dir)):
        raise Http404("File not found")
        
    if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
        return FileResponse(open(normalized_path, 'rb'))
    else:
        raise Http404("File not found")

def bcp_api_menu(request):
    """Returns BCP Menu items"""
    return JsonResponse(BCP_MENU, safe=False)

@csrf_exempt
def bcp_api_orders(request):
    """Creates a BCP order context and UPI payment parameters"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    import json
    import random
    import urllib.parse
    import datetime
    
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
        
    customer_name = data.get('customerName')
    customer_phone = data.get('customerPhone')
    customer_email = data.get('customerEmail')
    delivery_address = data.get('deliveryAddress')
    items = data.get('items', [])
    
    if not customer_name or not customer_phone or not delivery_address or not items:
        return JsonResponse({'error': 'Missing required checkout information.'}, status=400)
        
    calculated_items = []
    total_amount = 0
    
    for client_item in items:
        item_id = client_item.get('id')
        qty = client_item.get('quantity', 0)
        menu_item = next((m for m in BCP_MENU if m['id'] == item_id), None)
        if not menu_item:
            return JsonResponse({'error': f'Invalid menu item ID: {item_id}'}, status=400)
        
        item_total = menu_item['price'] * qty
        total_amount += item_total
        calculated_items.append({
            'id': menu_item['id'],
            'name': menu_item['name'],
            'price': menu_item['price'],
            'unit': menu_item['unit'],
            'quantity': qty
        })
        
    order_id = 'BCP-' + str(random.randint(100000, 999999))
    config = bcp_read_env()
    upi_id = config.get('UPI_ID', '9899946076@okbizaxis')
    merchant_name = config.get('MERCHANT_NAME', 'Bharat Chicken Point')
    
    encoded_name = urllib.parse.quote(merchant_name)
    encoded_note = urllib.parse.quote(f'Order {order_id}')
    upi_string = f"upi://pay?pa={upi_id}&pn={encoded_name}&am={total_amount:.2f}&cu=INR&tn={encoded_note}"
    
    new_order = {
        'id': order_id,
        'customerName': customer_name,
        'customerPhone': customer_phone,
        'customerEmail': customer_email or 'no-email@bcp.local',
        'deliveryAddress': delivery_address,
        'items': calculated_items,
        'totalAmount': total_amount,
        'status': 'Pending Payment',
        'createdAt': datetime.datetime.utcnow().isoformat() + 'Z',
        'upiPaymentLink': upi_string,
        'paymentDetails': None
    }
    
    orders = bcp_read_db('orders.json')
    orders.append(new_order)
    bcp_write_db('orders.json', orders)
    
    return JsonResponse({
        'success': True,
        'orderId': order_id,
        'totalAmount': total_amount,
        'upiPaymentLink': upi_string,
        'upiId': upi_id,
        'merchantName': merchant_name
    })

@csrf_exempt
def bcp_api_verify_payment(request, order_id):
    """Verifies simulated payment from frontend and triggers receipts logs/emails"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    import json
    import random
    import datetime
    
    try:
        data = json.loads(request.body)
    except Exception:
        data = {}
        
    utr = data.get('utr')
    payment_method = data.get('paymentMethod', 'UPI')
    
    orders = bcp_read_db('orders.json')
    order_index = next((i for i, o in enumerate(orders) if o['id'] == order_id), -1)
    
    if order_index == -1:
        return JsonResponse({'error': 'Order not found.'}, status=404)
        
    order = orders[order_index]
    order['status'] = 'Paid'
    order['paymentDetails'] = {
        'method': payment_method,
        'utr': utr or ('UTR-' + str(random.randint(100000000000, 999999999999))),
        'paidAt': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    
    orders[order_index] = order
    bcp_write_db('orders.json', orders)
    
    customer_html = bcp_get_customer_email_template(order)
    vendor_html = bcp_get_vendor_email_template(order)
    
    if order['customerEmail'] and order['customerEmail'] != 'no-email@bcp.local':
        bcp_send_notification_email(
            to=order['customerEmail'],
            subject=f"Order Confirmed! Your Receipt from Bharat Chicken Point [{order['id']}]",
            html_body=customer_html,
            email_type='Customer Confirmation'
        )
        
    config = bcp_read_env()
    vendor_email = config.get('VENDOR_EMAIL', 'sarfarajguddu.bcp@gmail.com')
    bcp_send_notification_email(
        to=vendor_email,
        subject=f"⚠️ NEW ORDER ALREADY PAID: {order['id']} | ₹{order['totalAmount']}",
        html_body=vendor_html,
        email_type='Vendor Notification'
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Payment verified and order confirmed.',
        'order': order
    })

def bcp_api_admin_orders(request):
    """Returns sorted lists of all orders for Vendor dashboard"""
    orders = bcp_read_db('orders.json')
    try:
        orders.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    except Exception:
        pass
    return JsonResponse(orders, safe=False)

@csrf_exempt
def bcp_api_admin_order_status(request, order_id):
    """Updates BCP order cooking and delivery status from Vendor dashboard"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    import json
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
    status = data.get('status')
    valid_statuses = ['Pending Payment', 'Paid', 'Cooking', 'Out for Delivery', 'Delivered', 'Cancelled']
    if status not in valid_statuses:
        return JsonResponse({'error': 'Invalid order status.'}, status=400)
        
    orders = bcp_read_db('orders.json')
    order_index = next((i for i, o in enumerate(orders) if o['id'] == order_id), -1)
    
    if order_index == -1:
        return JsonResponse({'error': 'Order not found.'}, status=404)
        
    orders[order_index]['status'] = status
    bcp_write_db('orders.json', orders)
    
    return JsonResponse({
        'success': True,
        'message': f'Order status updated to {status}.',
        'order': orders[order_index]
    })

def bcp_api_admin_emails(request):
    """Returns saved simulated email logs for Admin review"""
    logs = bcp_read_db('email_logs.json')
    return JsonResponse(logs, safe=False)

@csrf_exempt
def bcp_api_admin_config_smtp(request):
    """Saves SMTP credentials directly to BCP .env configuration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    import json
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
    host = data.get('host')
    port = data.get('port')
    user = data.get('user')
    passwd = data.get('pass')
    is_enabled = data.get('isEnabled')
    vendor_email = data.get('vendorEmail')
    
    config = bcp_read_env()
    config['IS_SMTP_ENABLED'] = 'true' if is_enabled else 'false'
    if host: config['SMTP_HOST'] = str(host)
    if port: config['SMTP_PORT'] = str(port)
    if user: config['SMTP_USER'] = str(user)
    if passwd: config['SMTP_PASS'] = str(passwd)
    if vendor_email: config['VENDOR_EMAIL'] = str(vendor_email)
    
    success = bcp_write_env(config)
    if success:
        return JsonResponse({'success': True, 'message': 'SMTP settings updated successfully.'})
    else:
        return JsonResponse({'error': 'Failed to save SMTP configuration.'}, status=500)






