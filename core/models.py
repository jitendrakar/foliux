from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from encrypted_model_fields.fields import (
    EncryptedCharField,
    EncryptedDateField,
    EncryptedEmailField,
    EncryptedTextField,
)

class Instrument(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=50, unique=True)
    isin = models.CharField(max_length=50, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    last_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    price_change = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    previous_close = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    pe_ratio = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    high_52w = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    diff_from_lh_pct = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.symbol

    def save(self, *args, **kwargs):
        if self.symbol:
            self.symbol = self.symbol.strip().upper()
        super().save(*args, **kwargs)

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    avg_cost = models.DecimalField(max_digits=10, decimal_places=2)
    ltp = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Last Traded Price
    notes = models.TextField(blank=True, null=True)
    
    @property
    def invested_amount(self):
        return self.quantity * self.avg_cost

    @property
    def current_value(self):
        return self.quantity * self.ltp

    @property
    def unrealized_pnl(self):
        return self.current_value - self.invested_amount
        
    @property
    def unrealized_pnl_percentage(self):
        if self.invested_amount == 0:
            return 0
        return (self.unrealized_pnl / self.invested_amount) * 100

    class Meta:
        unique_together = ('user', 'instrument')

TRADE_TYPES = [
    ('NORMAL', 'Normal'),
    ('INTRADAY', 'Intraday'),
]

class PnLStatement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    entry_date = models.DateField(null=True, blank=True)
    exit_date = models.DateField()
    quantity = models.IntegerField()
    buy_value = models.DecimalField(max_digits=15, decimal_places=2)
    sell_value = models.DecimalField(max_digits=15, decimal_places=2)
    realized_profit = models.DecimalField(max_digits=15, decimal_places=2)
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES, default='NORMAL')
    
    
    def __str__(self):
        return f"{self.user.username} - {self.instrument.symbol} - {self.realized_profit}"
        return f"{self.user.username} - {self.instrument.symbol} - {self.realized_profit}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = EncryptedCharField(max_length=100, null=True, blank=True)
    mobile_number = EncryptedCharField(max_length=15, null=True, blank=True)
    date_of_birth = EncryptedDateField(null=True, blank=True)
    gender = EncryptedCharField(max_length=10, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    investor_type = models.CharField(max_length=20, choices=[('conservative','Conservative'),('moderate','Moderate'),('growth','Growth'),('aggressive','Aggressive')], default='moderate')
    initial_investment_limit = models.DecimalField(max_digits=15, decimal_places=2, default=15000.00)
    mf_investment_limit = models.DecimalField(max_digits=15, decimal_places=2, default=100000.00)
    coin_investment_limit = models.DecimalField(max_digits=15, decimal_places=2, default=15000.00)
    equity_profit_expectation = models.DecimalField(max_digits=10, decimal_places=2, default=22.00)
    mf_profit_expectation = models.DecimalField(max_digits=10, decimal_places=2, default=22.00)
    coin_profit_expectation = models.DecimalField(max_digits=10, decimal_places=2, default=22.00)
    equity_fixed_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    equity_brokerage_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, null=True, blank=True) # Percentage (e.g., 0.2%)
    intraday_fixed_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    intraday_brokerage_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, null=True, blank=True) # Percentage (e.g., 0.2%)
    financial_goal = models.DecimalField(max_digits=20, decimal_places=2, default=10000000.00)
    theme = models.CharField(max_length=10, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.profile_picture:
            try:
                from PIL import Image
                img = Image.open(self.profile_picture.path)
                
                # Crop to square
                width, height = img.size
                if width != height:
                    min_dim = min(width, height)
                    left = (width - min_dim) / 2
                    top = (height - min_dim) / 2
                    right = (width + min_dim) / 2
                    bottom = (height + min_dim) / 2
                    img = img.crop((left, top, right, bottom))

                # Resize to high quality
                if img.height > 600 or img.width > 600:
                    output_size = (600, 600)
                    img.thumbnail(output_size, Image.Resampling.LANCZOS)
                
                img.save(self.profile_picture.path, quality=95, optimize=True)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing profile picture: {e}")

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def is_complete(self):
        """Check if all mandatory profile fields are filled."""
        mandatory_fields = [
            self.full_name,
            self.mobile_number,
            self.date_of_birth,
            self.gender,
        ]
        if not all(mandatory_fields):
            return False
        if not self.profile_picture:
            return False
        return True

    def get_max_investment(self, strategy_key):
        """Return maximum investment per stock/ETF for the given strategy based on investor_type.
        strategy_key corresponds to the keys used in STRATEGY_SHEET_TABS (flexi, quant, pyramid, growth).
        Initial investment limit is used as the base (moderate) and scaled for other types.
        """
        base = float(self.initial_investment_limit)
        multipliers = {
            'conservative': {'flexi': 2.0, 'pyramid': 1.0, 'quant': 0.67, 'growth': 0.33},
            'moderate': {'flexi': 1.0, 'pyramid': 1.0, 'quant': 1.0, 'growth': 1.0},
            'growth': {'flexi': 0.67, 'pyramid': 1.0, 'quant': 1.33, 'growth': 2.0},
            'aggressive': {'flexi': 0.33, 'pyramid': 1.0, 'quant': 2.0, 'growth': 3.33},
        }
        strategy_multiplier = multipliers.get(self.investor_type, multipliers['moderate']).get(strategy_key, 1.0)
        return Decimal(str(round(base * strategy_multiplier, 2)))

# Signals to automatically create/save Profile
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, raw, **kwargs):
    if raw:
        return
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, raw, **kwargs):
    if raw:
        return
    if hasattr(instance, 'profile'):
        instance.profile.save()

import logging
logger = logging.getLogger(__name__)

from django.db.models.signals import pre_save
@receiver(pre_save, sender=User)
def track_password_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_user = User.objects.get(pk=instance.pk)
            if old_user.password != instance.password:
                logger.info(f"Password changing for user {instance.username}: {old_user.password[:10]} -> {instance.password[:10]}")
                
                # SHIELD: If user had a usable password, and it's being set to UNUSABLE (starts with !),
                # and this is NOT a deliberate logout/unusable set we expect, restore it.
                if not old_user.password.startswith('!') and instance.password.startswith('!'):
                    logger.warning(f"Restoring usable password for {instance.username} (was about to be set to unusable)")
                    instance.password = old_user.password
        except User.DoesNotExist:
            pass

from allauth.socialaccount.signals import social_account_added, social_account_updated
@receiver(social_account_added)
@receiver(social_account_updated)
def protect_password_on_social_link(request, sociallogin, **kwargs):
    user = sociallogin.user
    if user.pk:
        # Check if user had a usable password before (this is tricky because signal is 'added')
        # But we can at least log it.
        logger.info(f"Social account linked/updated for {user.username}. Provider: {sociallogin.account.provider}")
class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = EncryptedCharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        from django.utils import timezone
        import datetime
        # Valid for 20 minutes
        return self.created_at >= timezone.now() - datetime.timedelta(minutes=20)

    def __str__(self):
        return f"OTP for {self.user.username} - {self.code}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES, default='NORMAL')
    quantity = models.IntegerField()
    remaining_quantity = models.IntegerField(default=0) # Only for BUY
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    matched_buy = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='matched_sells') # For SELL transactions to specify a lot
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'created_at']

    def __str__(self):
        return f"{self.user.username} {self.transaction_type} {self.quantity} {self.instrument.symbol} @ {self.price} on {self.date}"


class SignupOTP(models.Model):
    """OTP sent to an email address BEFORE a user account is created."""
    email = EncryptedEmailField()
    code = EncryptedCharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return self.created_at >= timezone.now() - timedelta(minutes=20)

    def __str__(self):
        return f"SignupOTP for {self.email} - {self.code}"

class MarketTicker(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    change = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    percent_change = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Strategy(models.Model):
    name = models.CharField(max_length=50, unique=True) # e.g., 'flexi', 'quant', 'pyramid', 'growth'
    display_name = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

class StrategyStock(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='stocks')
    symbol = models.CharField(max_length=20) # We store symbol string to avoid hard dependency on Instrument object during sync if it doesn't exist yet
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = ('strategy', 'symbol')
        ordering = ['order']

    def __str__(self):
        return f"{self.strategy.name} - {self.symbol}"

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'instrument')

    def __str__(self):
        return f"{self.user.username} watching {self.instrument.symbol}"

class UserReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.rating} Stars"

class Dividend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dividends')
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    ex_date = models.DateField(null=True, blank=True)
    received_date = models.DateField()
    
    def __str__(self):
        return f"{self.user.username} - {self.instrument.symbol} - {self.amount}"

class InvestmentGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=20, decimal_places=2)
    target_date = models.DateField()
    current_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"

class CorporateAction(models.Model):
    ACTION_TYPES = [
        ('DIVIDEND', 'Dividend Declared'),
        ('INTERIM_DIVIDEND', 'Interim Dividend'),
        ('BONUS', 'Bonus Issue'),
        ('SPLIT', 'Stock Split'),
        ('RIGHTS_ISSUE', 'Rights Issue'),
        ('BUYBACK', 'Buyback'),
        ('MERGER', 'Merger'),
        ('DEMERGER', 'Demerger'),
        ('AMALGAMATION', 'Amalgamation'),
        ('DELISTING', 'Delisting'),
        ('OPEN_OFFER', 'Open Offer / Takeover'),
        ('FV_CHANGE', 'Face Value Change / Reverse Split'),
        ('PREF_ALLOTMENT', 'Preferential Allotment'),
        ('ESOP', 'ESOP / Share Dilution'),
        ('SPECIAL_DIVIDEND', 'Special Dividend'),
        ('SHARE_QUANTITY', 'Share Quantity'),
        ('SHARE_PRICE', 'Share Price'),
        ('OWNERSHIP_PCT', 'Ownership Percentage'),
        ('CASH_BENEFIT', 'Cash Benefit'),
        ('CO_STRUCTURE', 'Company Structure'),
        ('TRADING_STATUS', 'Trading / Liquidity Status'),
    ]
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name='corporate_actions')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    ratio_numerator = models.IntegerField(null=True, blank=True) # e.g., 2 for a 2:1 split
    ratio_denominator = models.IntegerField(null=True, blank=True) # e.g., 1 for a 2:1 split
    announcement_date = models.DateField()
    ex_date = models.CharField(max_length=50, null=True, blank=True, default="Not Yet Declared", help_text="Enter date (YYYY-MM-DD) or 'Not Yet Declared'")
    record_date = models.CharField(max_length=50, null=True, blank=True, default="Not Yet Declared", help_text="Enter date (YYYY-MM-DD) or 'Not Yet Declared'")
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.instrument.symbol} - {self.action_type} - {self.announcement_date}"

class SignalNotificationState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='signal_notification_state')
    last_buy_count = models.IntegerField(default=0)
    last_reduce_count = models.IntegerField(default=0)
    last_sell_count = models.IntegerField(default=0)
    last_signals_hash = models.CharField(max_length=64, null=True, blank=True)
    last_notified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Buy:{self.last_buy_count} Reduce:{self.last_reduce_count} Sell:{self.last_sell_count}"

class FamilyLink(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_links')
    family_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linked_to_family')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'family_user')

    def __str__(self):
        return f"{self.user.username} -> {self.family_user.username} ({'Verified' if self.is_verified else 'Pending'})"

class FinancialYearData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_year_data')
    financial_year = models.CharField(max_length=9) # Format: '2023-2024'
    invested_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    current_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    realized_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    is_locked = models.BooleanField(default=False)
    edit_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'financial_year')
        ordering = ['-financial_year']

    def __str__(self):
        return f"{self.user.username} - {self.financial_year}"

class MutualFund(models.Model):
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=50, unique=True) # Yahoo Symbol (e.g. 0P0000XWWI.BO)
    scheme_code = models.CharField(max_length=20, unique=True, null=True, blank=True) # For mfapi.in
    isin = models.CharField(max_length=20, unique=True, null=True, blank=True)
    amc = models.CharField(max_length=100, null=True, blank=True)
    nav = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    prev_nav = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_nav_history(self):
        """Fetch NAV history from cache or API."""
        if not self.scheme_code:
            return []
            
        from django.core.cache import cache
        cache_key = f"mf_history_{self.scheme_code}"
        history = cache.get(cache_key)
        
        if history:
            return history
            
        from .mf_utils import get_mf_details
        details = get_mf_details(self.scheme_code)
        if details and details.get('data'):
            history = details['data']
            # Cache for 1 day
            cache.set(cache_key, history, 86400)
            return history
        return []

class MutualFundScheme(models.Model):
    scheme_code = models.CharField(max_length=20, unique=True)
    scheme_name = models.CharField(max_length=300)
    isin_growth = models.CharField(max_length=50, null=True, blank=True)
    isin_div_reinvestment = models.CharField(max_length=50, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.scheme_code} - {self.scheme_name}"

class MFPortfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mf_portfolios')
    fund = models.ForeignKey(MutualFund, on_delete=models.CASCADE)
    units = models.DecimalField(max_digits=20, decimal_places=4)
    avg_nav = models.DecimalField(max_digits=20, decimal_places=4)
    realized_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    @property
    def day_change(self):
        if self.fund.prev_nav == 0: return 0
        return self.units * (self.fund.nav - self.fund.prev_nav)

    @property
    def day_change_pct(self):
        if self.fund.prev_nav == 0: return 0
        return ((self.fund.nav - self.fund.prev_nav) / self.fund.prev_nav) * 100
    @property
    def invested_amount(self):
        return self.units * self.avg_nav

    @property
    def current_value(self):
        return self.units * self.fund.nav

    @property
    def unrealized_pnl(self):
        return self.current_value - self.invested_amount

    @property
    def pnl_percentage(self):
        if self.invested_amount == 0: return 0
        return (self.unrealized_pnl / self.invested_amount) * 100

    class Meta:
        unique_together = ('user', 'fund')

class MFTransaction(models.Model):
    TRANSACTION_TYPES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mf_transactions')
    fund = models.ForeignKey(MutualFund, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    units = models.DecimalField(max_digits=20, decimal_places=4)
    price = models.DecimalField(max_digits=20, decimal_places=4)
    date = models.DateField()
    remaining_units = models.DecimalField(max_digits=20, decimal_places=4, default=0) # Only for BUY
    is_sip = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Coin(models.Model):
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=50, unique=True) # Yahoo Symbol (e.g. BTC-INR)
    price = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    prev_price = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_price_history(self, period='1y'):
        """Fetch historical prices from Yahoo Finance."""
        from django.core.cache import cache
        cache_key = f"coin_history_{self.symbol}_{period}"
        history = cache.get(cache_key)
        
        if history:
            return history
            
        import yfinance as yf
        import pandas as pd
        try:
            ticker = yf.Ticker(self.symbol)
            hist = ticker.history(period=period)
            if not hist.empty:
                # Convert to simple list of dicts for template
                history_data = []
                for dt, row in hist.iterrows():
                    history_data.append({
                        'date': dt.strftime('%Y-%m-%d'),
                        'price': float(row['Close'])
                    })
                # Cache for 6 hours
                cache.set(cache_key, history_data, 21600)
                return history_data
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching history for {self.symbol}: {e}")
            
        return []

class CoinPortfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_portfolios')
    coin = models.ForeignKey(Coin, on_delete=models.CASCADE)
    units = models.DecimalField(max_digits=20, decimal_places=8) # More precision for crypto
    avg_price = models.DecimalField(max_digits=20, decimal_places=4)
    realized_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    @property
    def day_change(self):
        if self.coin.prev_price == 0: return 0
        return self.units * (self.coin.price - self.coin.prev_price)

    @property
    def invested_amount(self):
        return self.units * self.avg_price

    @property
    def current_value(self):
        return self.units * self.coin.price

    @property
    def unrealized_pnl(self):
        return self.current_value - self.invested_amount

    @property
    def pnl_percentage(self):
        if self.invested_amount == 0: return 0
        return (self.unrealized_pnl / self.invested_amount) * 100

    class Meta:
        unique_together = ('user', 'coin')

class CoinTransaction(models.Model):
    TRANSACTION_TYPES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_transactions')
    coin = models.ForeignKey(Coin, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    units = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=4)
    date = models.DateField()
    remaining_units = models.DecimalField(max_digits=20, decimal_places=8, default=0) # Only for BUY
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_value(self):
        return self.units * self.price

class NPSFund(models.Model):
    name = models.CharField(max_length=200, unique=True)
    scheme_code = models.CharField(max_length=20, null=True, blank=True) # From npsnav.in
    nav = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    prev_nav = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_nav_history(self):
        """Fetch NAV history from npsnav.in API."""
        if not self.scheme_code:
            return []
            
        from django.core.cache import cache
        cache_key = f"nps_history_{self.scheme_code}"
        history = cache.get(cache_key)
        
        if history:
            return history
            
        import requests
        url = f"https://npsnav.in/api/historical/{self.scheme_code}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    history_data = [{'date': d[0], 'nav': d[1]} for d in data]
                    cache.set(cache_key, history_data, 86400)
                    return history_data
        except Exception:
            pass
        return []

class NPSPortfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nps_portfolios')
    fund = models.ForeignKey(NPSFund, on_delete=models.CASCADE)
    units = models.DecimalField(max_digits=20, decimal_places=4)
    avg_nav = models.DecimalField(max_digits=20, decimal_places=4)
    realized_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    @property
    def day_change(self):
        if self.fund.prev_nav == 0: return 0
        return self.units * (self.fund.nav - self.fund.prev_nav)

    @property
    def invested_amount(self):
        return self.units * self.avg_nav

    @property
    def current_value(self):
        return self.units * self.fund.nav

    @property
    def unrealized_pnl(self):
        return self.current_value - self.invested_amount

    @property
    def pnl_percentage(self):
        if self.invested_amount == 0: return 0
        return (self.unrealized_pnl / self.invested_amount) * 100

    class Meta:
        unique_together = ('user', 'fund')

class NPSTransaction(models.Model):
    TRANSACTION_TYPES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nps_transactions')
    fund = models.ForeignKey(NPSFund, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    units = models.DecimalField(max_digits=20, decimal_places=4)
    price = models.DecimalField(max_digits=20, decimal_places=4)
    date = models.DateField()
    remaining_units = models.DecimalField(max_digits=20, decimal_places=4, default=0) # Only for BUY
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_value(self):
        return self.units * self.price

class FixedAsset(models.Model):
    ASSET_TYPES = [
        ('FD', 'Fixed Deposit'),
        ('RD', 'Recurring Deposit'),
        ('PPF', 'PPF'),
        ('EPF', 'EPF/PF'),
        ('Other', 'Other Fixed Asset')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fixed_assets')
    parent_asset = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='renewals')
    instrument_name = EncryptedCharField(max_length=100)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES, default='FD')
    # Stored encrypted as strings; use .invested_amount_decimal / .interest_rate_decimal properties
    invested_amount = EncryptedCharField(max_length=50)
    interest_rate = EncryptedCharField(max_length=20)
    investment_date = models.DateField()
    maturity_date = models.DateField(null=True, blank=True)
    
    # RD specific fields
    monthly_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=0) # Only for RD/PPF if monthly
    tenure_years = models.IntegerField(default=0)
    next_deposit_date = models.DateField(null=True, blank=True)
    
    # New fields
    holder_name = EncryptedCharField(max_length=100, null=True, blank=True)
    fd_id = EncryptedCharField(max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def _d(self, val):
        """Safely convert encrypted string field to Decimal."""
        try:
            return Decimal(str(val)) if val not in (None, '', 'None') else Decimal('0')
        except Exception:
            return Decimal('0')

    @property
    def invested_amount_decimal(self):
        return self._d(self.invested_amount)

    @property
    def interest_rate_decimal(self):
        return self._d(self.interest_rate)

    @property
    def current_value(self):
        from datetime import date
        today = date.today()
        # Helper: safely get float from encrypted string field
        try:
            inv = float(self.invested_amount) if self.invested_amount else 0.0
        except (ValueError, TypeError):
            inv = 0.0
        try:
            ir = float(self.interest_rate) if self.interest_rate else 0.0
        except (ValueError, TypeError):
            ir = 0.0

        # Interest compounding stops at the maturity date if it has passed
        calculation_date = min(today, self.maturity_date) if self.maturity_date else today
        
        # Monthly interest rate
        i = ir / 100 / 12
        
        if self.asset_type == 'RD':
            n = max(0, (calculation_date.year - self.investment_date.year) * 12 + (calculation_date.month - self.investment_date.month))
            if n == 0: return inv
            monthly_val = float(self.monthly_deposit or 0)
            if monthly_val <= 0: return inv
            total = 0
            for month in range(1, n + 2):
                months_active = (n + 1) - month
                if months_active < 0: break
                total += monthly_val * ((1 + i) ** months_active)
            return total
        else:
            months = max(0, (calculation_date.year - self.investment_date.year) * 12 + (calculation_date.month - self.investment_date.month))
            return inv * ((1 + i) ** months)
        
    @property
    def is_matured(self):
        from datetime import date
        if self.maturity_date:
            return date.today() >= self.maturity_date
        return False

    @property
    def unrealized_pnl(self):
        try:
            inv = float(self.invested_amount) if self.invested_amount else 0.0
        except (ValueError, TypeError):
            inv = 0.0
        return self.current_value - inv

    @property
    def pnl_percentage(self):
        try:
            inv = float(self.invested_amount) if self.invested_amount else 0.0
        except (ValueError, TypeError):
            inv = 0.0
        if inv == 0: return 0
        return (self.unrealized_pnl / inv) * 100

    def value_at_date(self, target_date):
        if target_date < self.investment_date:
            return Decimal('0')
        
        calculation_date = min(target_date, self.maturity_date) if self.maturity_date else target_date
        
        try:
            inv = float(self.invested_amount) if self.invested_amount else 0.0
        except (ValueError, TypeError):
            inv = 0.0
        try:
            ir = float(self.interest_rate) if self.interest_rate else 0.0
        except (ValueError, TypeError):
            ir = 0.0
            
        i = ir / 100 / 12
        
        if self.asset_type == 'RD':
            n = max(0, (calculation_date.year - self.investment_date.year) * 12 + (calculation_date.month - self.investment_date.month))
            if n == 0: return Decimal(str(inv))
            monthly_val = float(self.monthly_deposit or 0)
            if monthly_val <= 0: return Decimal(str(inv))
            total = 0
            for month in range(1, n + 2):
                months_active = (n + 1) - month
                if months_active < 0: break
                total += monthly_val * ((1 + i) ** months_active)
            return Decimal(str(total))
        else:
            months = max(0, (calculation_date.year - self.investment_date.year) * 12 + (calculation_date.month - self.investment_date.month))
            return Decimal(str(inv * ((1 + i) ** months)))

    def __str__(self):
        return f"{self.user.username} - {self.instrument_name}"

class OtherAsset(models.Model):
    ASSET_TYPES = [
        ('Plot', 'Plot'),
        ('Flat', 'Flat'),
        ('Gold', 'Gold'),
        ('Silver', 'Silver'),
        ('Land', 'Land'),
        ('Commercial', 'Commercial Unit'),
        ('Other', 'Other Physical Asset'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='other_assets')
    name = models.CharField(max_length=100) # e.g. "Green Valley Plot"
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES, default='Other')
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=20, decimal_places=2)
    actual_market_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    expected_appreciation = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    monthly_rent = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # New fields for identification
    holder_name = EncryptedCharField(max_length=100, null=True, blank=True)
    asset_id = EncryptedCharField(max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def estimated_market_value(self):
        from datetime import date
        from decimal import Decimal
        import calendar
        
        today = date.today()
        if today < self.purchase_date:
            return self.purchase_price
            
        months = (today.year - self.purchase_date.year) * 12 + (today.month - self.purchase_date.month)
        if today.day < self.purchase_date.day:
            last_day_of_month = calendar.monthrange(today.year, today.month)[1]
            if today.day != last_day_of_month:
                months -= 1
        months = max(0, months)
        
        rate = (self.expected_appreciation or Decimal('0')) / Decimal('100') / Decimal('12')
        val = Decimal(str(self.purchase_price)) * ((Decimal('1') + rate) ** months)
        return val.quantize(Decimal('0.01'))

    @property
    def current_value(self):
        est = self.estimated_market_value
        if self.actual_market_value is not None:
            return max(self.actual_market_value, est)
        return est

    @current_value.setter
    def current_value(self, value):
        self.actual_market_value = value
    
    @property
    def unrealized_pnl(self):
        return float(self.current_value) - float(self.purchase_price)

    @property
    def pnl_percentage(self):
        if self.purchase_price == 0: return 0
        return (self.unrealized_pnl / float(self.purchase_price)) * 100

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.asset_type})"

class Loan(models.Model):
    LOAN_CATEGORIES = [
        ('Home', 'Home Loan'),
        ('Car', 'Car Loan'),
        ('Personal', 'Personal Loan'),
        ('Education', 'Education Loan'),
        ('Gold', 'Gold Loan'),
        ('Other', 'Other Loan'),
    ]
    INTEREST_TYPES = [('Reducing', 'Reducing'), ('Flat', 'Flat')]
    INTEREST_LOCKS = [('Fixed', 'Fixed'), ('Floating', 'Floating')]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    bank_name = EncryptedCharField(max_length=100)
    category = models.CharField(max_length=50, choices=LOAN_CATEGORIES, default='Personal')
    # Stored encrypted as strings
    loan_amount = EncryptedCharField(max_length=50)
    start_date = models.DateField()
    interest_rate = EncryptedCharField(max_length=20)
    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPES, default='Reducing')
    tenure_months = models.IntegerField()
    emi_amount = EncryptedCharField(max_length=50)
    interest_lock = models.CharField(max_length=20, choices=INTEREST_LOCKS, default='Fixed')
    next_emi_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.bank_name} ({self.category})"

    def _d(self, val):
        """Safely convert encrypted string field to Decimal."""
        try:
            return Decimal(str(val)) if val not in (None, '', 'None') else Decimal('0')
        except Exception:
            return Decimal('0')

    @property
    def loan_amount_decimal(self):
        return self._d(self.loan_amount)

    @property
    def interest_rate_decimal(self):
        return self._d(self.interest_rate)

    @property
    def emi_amount_decimal(self):
        return self._d(self.emi_amount)

    @property
    def total_paid_till_date(self):
        return sum(p.amount_decimal for p in self.payments.all())

    @property
    def total_interest_paid(self):
        return sum(p.interest_component_decimal for p in self.payments.all())

    @property
    def total_principal_paid(self):
        return sum(p.principal_component_decimal for p in self.payments.all())

    @property
    def current_outstanding(self):
        return self.loan_amount_decimal - self.total_principal_paid

    @property
    def progress_percentage(self):
        la = self.loan_amount_decimal
        if la == 0: return 0
        return (self.total_principal_paid / la) * 100

    @property
    def remaining_tenure_months(self):
        emi = self.emi_amount_decimal
        out = self.current_outstanding
        if emi <= 0 or out <= 0: return 0
        if self.interest_type == 'Flat':
            la = self.loan_amount_decimal
            ir = self.interest_rate_decimal
            total_payable = la + (la * ir / 100 * self.tenure_months / 12)
            remaining_to_pay = total_payable - self.total_paid_till_date
            return int(remaining_to_pay / emi)
        else:
            import math
            P = float(out)
            r = float(self.interest_rate_decimal) / 100 / 12
            E = float(emi)
            if E <= P * r: return 999
            try:
                n = -math.log(1 - (P * r / E)) / math.log(1 + r)
                return int(math.ceil(n))
            except Exception:
                return 0

class LoanPayment(models.Model):
    PAYMENT_TYPES = [('EMI', 'EMI'), ('Prepayment', 'Prepayment')]
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='EMI')
    # Stored encrypted as strings
    amount = EncryptedCharField(max_length=50)
    date = models.DateField()
    principal_component = EncryptedCharField(max_length=50)
    interest_component = EncryptedCharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def _d(self, val):
        try:
            return Decimal(str(val)) if val not in (None, '', 'None') else Decimal('0')
        except Exception:
            return Decimal('0')

    @property
    def amount_decimal(self):
        return self._d(self.amount)

    @property
    def principal_component_decimal(self):
        return self._d(self.principal_component)

    @property
    def interest_component_decimal(self):
        return self._d(self.interest_component)

    class Meta:
        ordering = ['date', 'created_at']

class MFSIP(models.Model):
    """Systematic Investment Plan (SIP) for Mutual Funds."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mf_sips')
    fund = models.ForeignKey(MutualFund, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    sip_date = models.IntegerField(help_text="Day of the month (1-28)")
    next_execution_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_executed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.fund.name} SIP (₹{self.amount})"

class PortfolioValueHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio_history')
    date = models.DateField(default=timezone.now)
    invested_value = models.DecimalField(max_digits=20, decimal_places=2)
    current_value = models.DecimalField(max_digits=20, decimal_places=2)
    
    # Separated Valuations
    stock_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    stock_current = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    mf_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    mf_current = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    coin_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    coin_current = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    nps_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    nps_current = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    net_worth = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    nifty_price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.current_value}"

class IPO(models.Model):
    ADVISE_CHOICES = [
        ('APPLY', 'Apply'),
        ('NON_APPLY', 'Non Apply'),
        ('WAITING', 'Waiting'),
    ]
    
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    company_work = models.TextField(help_text="What company does – short text")
    notes = models.TextField(help_text="Post / Analysis")
    advise = models.CharField(max_length=20, choices=ADVISE_CHOICES, default='WAITING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def status(self):
        from django.utils import timezone
        today = timezone.localdate()
        if today < self.start_date:
            return 'Upcoming'
        elif self.start_date <= today <= self.end_date:
            return 'Open'
        else:
            return 'Closed'

    class Meta:
        ordering = ['-start_date']
        verbose_name = "IPO"
        verbose_name_plural = "IPOs"

class ChatbotKnowledge(models.Model):
    question = models.TextField(help_text="Expected matching words/phrases")
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Q: {self.question[:50]}..."

    class Meta:
        verbose_name = "Chatbot Knowledge"
        verbose_name_plural = "Chatbot Knowledge Base"

class HiddenSignal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidden_signals')
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'instrument')

    def __str__(self):
        return f"{self.user.username} - Hidden: {self.instrument.symbol}"

class NewsAlert(models.Model):
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name='news_alerts')
    message_id = models.CharField(max_length=255, unique=True) # Gmail Message ID to prevent duplicates
    title = models.CharField(max_length=255)
    summary = models.TextField()
    url = models.URLField(max_length=1000, null=True, blank=True)
    alert_type = models.CharField(max_length=50, null=True, blank=True) # e.g. Positive, Negative
    news_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.instrument.symbol} - {self.title}"


class EmailLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_logs')
    email_type = models.CharField(max_length=50)  # e.g., 'daily_stock_news'
    date_sent = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'email_type', 'date_sent')
        indexes = [
            models.Index(fields=['user', 'email_type', 'date_sent']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.email_type} - {self.date_sent}"


class MissingInstrumentRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='missing_instrument_requests')
    searched_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('reviewed', 'Reviewed')], default='pending')

    def __str__(self):
        return f"{self.user.username} - {self.searched_name} ({self.status})"


class BlogPost(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, help_text="SEO-friendly URL identifier. Generated automatically from title.")
    content = models.TextField(help_text="The body of the blog post. HTML or plain text.")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    excerpt = models.TextField(blank=True, null=True, help_text="A short summary of the post displayed on the list page.")
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True, help_text="Upload an image for the post.")
    image_url = models.URLField(max_length=1000, blank=True, null=True, help_text="Or paste an external image URL if not uploading.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')
    tags = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated list of tags (e.g. Stocks, Mutual Funds, Macroeconomy)")
    views_count = models.IntegerField(default=0)
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new_publish = False
        if self.status == 'published' and not self.email_sent:
            is_new_publish = True
            self.email_sent = True
        super().save(*args, **kwargs)
        if is_new_publish:
            from .utils import send_blog_notification
            send_blog_notification(self)

    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog_detail', kwargs={'slug': self.slug})


class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.title}"


class CashFlowEntry(models.Model):
    ENTRY_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('INVESTMENT', 'Investment')
    ]
    CATEGORIES = [
        # Income Categories
        ('SALARY', 'Salary'),
        ('RENTAL_INCOME', 'Rental Income'),
        ('INTEREST_INCOME', 'Interest Income'),
        ('DIVIDEND_INCOME', 'Dividend Income'),
        ('OTHER_INCOME', 'Other Income'),
        
        # Expense Categories
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
        
        # Investment Categories
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
        ('OTHER_INVESTMENTS', 'Other Investments')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cashflow_entries')
    date = models.DateField(default=timezone.localdate)
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.amount} on {self.date}"


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['key']),
        ]

    def __str__(self):
        return self.key


class UserTaxProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tax_profiles')
    financial_year = models.CharField(max_length=9) # e.g. '2025-2026'
    salary = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    business_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    other_taxable_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    agricultural_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    hra_received = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    rent_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    home_loan_interest = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    section_80c = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    section_80d = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    section_80ccd1b = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    section_80g = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    other_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'financial_year')

    def __str__(self):
        return f"{self.user.username} - {self.financial_year}"


class SavedCalculation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_calculations')
    calc_type = models.CharField(max_length=50) # e.g. 'sip', 'cagr', 'swp', 'emi'
    calc_name = models.CharField(max_length=100) # e.g. 'SIP Calculator'
    name = models.CharField(max_length=150) # custom name
    input_values = models.JSONField(default=dict)
    calculated_results = models.JSONField(default=dict)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.calc_name} - {self.name}"


class IncomeTaxBaseModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    financial_year = models.CharField(max_length=9) # e.g. '2025-26'
    source = models.CharField(max_length=50, default='AIS JSON')
    imported_on = models.DateTimeField(auto_now_add=True)
    json_reference = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class IncomeTaxProfile(IncomeTaxBaseModel):
    pan = models.CharField(max_length=50)
    aadhaar = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=255)
    dob = models.CharField(max_length=50) # DDMMYYYY or YYYY-MM-DD
    email = models.CharField(max_length=255, blank=True, null=True)
    mobile = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'income_tax_profile'
        verbose_name = 'Income Tax Profile'
        verbose_name_plural = 'Income Tax Profiles'


class IncomeTaxTds(IncomeTaxBaseModel):
    deductor_name = models.CharField(max_length=255, blank=True, null=True)
    tan = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=50, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    tax_deducted = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    tax_collected = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    quarter = models.CharField(max_length=50, blank=True, null=True) # e.g. 'Q1'

    class Meta:
        db_table = 'income_tax_tds'


class IncomeTaxSalary(IncomeTaxBaseModel):
    employer_name = models.CharField(max_length=255, blank=True, null=True)
    salary = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    perquisites = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    tax_deducted = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))

    class Meta:
        db_table = 'income_tax_salary'


class IncomeTaxInterest(IncomeTaxBaseModel):
    interest_type = models.CharField(max_length=50) # e.g. 'Savings', 'Fixed Deposit', 'Recurring Deposit', 'Post Office', 'Others'
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    tds = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'income_tax_interest'


class IncomeTaxDividend(IncomeTaxBaseModel):
    company_name = models.CharField(max_length=255, blank=True, null=True)
    isin = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'income_tax_dividend'


class IncomeTaxEquity(IncomeTaxBaseModel):
    broker = models.CharField(max_length=255, blank=True, null=True)
    isin = models.CharField(max_length=50, blank=True, null=True)
    buy_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    sell_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    quantity = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('0'))
    stcg = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    ltcg = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'income_tax_equity'


class IncomeTaxMutualFund(IncomeTaxBaseModel):
    amc = models.CharField(max_length=255, blank=True, null=True)
    scheme = models.CharField(max_length=255, blank=True, null=True)
    purchase = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    redemption = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    units = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('0'))
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))

    class Meta:
        db_table = 'income_tax_mutualfund'


class IncomeTaxSft(IncomeTaxBaseModel):
    transaction_type = models.CharField(max_length=100) # e.g. 'Cash Deposit', etc.
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'income_tax_sft'


class IncomeTaxTaxPaid(IncomeTaxBaseModel):
    tax_type = models.CharField(max_length=100) # e.g. 'Advance Tax', 'Self Assessment Tax'
    challan_details = models.TextField(blank=True, null=True)
    bsr_code = models.CharField(max_length=50, blank=True, null=True)
    challan_number = models.CharField(max_length=50, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))

    class Meta:
        db_table = 'income_tax_taxpaid'


class IncomeTaxRefund(IncomeTaxBaseModel):
    refund_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    date = models.DateField(blank=True, null=True)
    assessment_year = models.CharField(max_length=50) # e.g. '2025-26'
    status = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'income_tax_refund'


class IncomeTaxDemand(IncomeTaxBaseModel):
    assessment_year = models.CharField(max_length=50)
    outstanding_demand = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    status = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'income_tax_demand'


class IncomeTaxOther(IncomeTaxBaseModel):
    category = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'income_tax_other'








