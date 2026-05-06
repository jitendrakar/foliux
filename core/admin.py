from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import pandas as pd
from .models import (
    Instrument, Portfolio, PnLStatement, Profile, OTP, 
    Transaction, SignupOTP, MarketTicker, Strategy, 
    StrategyStock, Watchlist, Dividend, InvestmentGoal,
    CorporateAction, MutualFund, MFPortfolio, MFTransaction,
    Coin, CoinPortfolio, CoinTransaction,
    NPSFund, NPSPortfolio, NPSTransaction, IPO, ChatbotKnowledge,
    UserReview
)

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'isin', 'is_verified', 'last_price')
    search_fields = ('symbol', 'name', 'isin')
    list_filter = ('is_verified',)

    change_list_template = "admin/instrument_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            if not csv_file.name.endswith('.csv') and not csv_file.name.endswith('.xlsx'):
                messages.error(request, 'Only .csv or .xlsx files are allowed')
                return redirect("..")
            
            try:
                if csv_file.name.endswith('.csv'):
                    df = pd.read_csv(csv_file)
                else:
                    df = pd.read_excel(csv_file)
                
                # Required Fields: Company Name, NSE/BSE Code
                df.columns = [c.strip() for c in df.columns]
                
                required_cols = ['Company Name', 'NSE/BSE Code']
                if not all(col in df.columns for col in required_cols):
                    messages.error(request, f"Missing required columns: {required_cols}")
                    return redirect("..")

                count = 0
                for _, row in df.iterrows():
                    name = str(row['Company Name']).strip()
                    symbol = str(row['NSE/BSE Code']).strip().upper()
                    
                    if symbol:
                        Instrument.objects.update_or_create(
                            symbol=symbol,
                            defaults={
                                'name': name,
                                'is_verified': True
                            }
                        )
                        count += 1
                
                self.message_user(request, f"Successfully imported {count} verified instruments.")
                return redirect("..")
            except Exception as e:
                self.message_user(request, f"Error importing: {e}", level=messages.ERROR)
                return redirect("..")

        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'quantity', 'avg_cost', 'ltp')
    search_fields = ('user__username', 'instrument__symbol')
    list_filter = ('user',)

@admin.register(PnLStatement)
class PnLStatementAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'realized_profit', 'exit_date')
    search_fields = ('user__username', 'instrument__symbol')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'investor_type')
    search_fields = ('user__username', 'full_name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'transaction_type', 'quantity', 'price', 'date')
    list_filter = ('transaction_type', 'date')
    search_fields = ('user__username', 'instrument__symbol')

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'updated_at')

@admin.register(StrategyStock)
class StrategyStockAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'symbol', 'order')
    list_filter = ('strategy',)

@admin.register(MarketTicker)
class MarketTickerAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'change', 'updated_at')

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'added_at')
    list_filter = ('user',)

@admin.register(Dividend)
class DividendAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'amount', 'received_date')
    list_filter = ('user', 'received_date')

@admin.register(InvestmentGoal)
class InvestmentGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'target_amount', 'current_amount', 'target_date')
    list_filter = ('user', 'target_date')

@admin.register(CorporateAction)
class CorporateActionAdmin(admin.ModelAdmin):
    list_display = ('instrument', 'action_type', 'announcement_date', 'ex_date', 'record_date')
    list_filter = ('action_type', 'announcement_date')
    search_fields = ('instrument__symbol',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:  # Only for new additions
            self.send_corporate_action_email(obj)

    def send_corporate_action_email(self, obj):
        from .models import Portfolio, Profile
        from django.core.mail import send_mail
        from django.conf import settings
        import logging

        logger = logging.getLogger(__name__)

        # Find users who hold this instrument
        holders = Portfolio.objects.filter(instrument=obj.instrument, quantity__gt=0).select_related('user')
        
        subject = f"Corporate Action: {obj.get_action_type_display()} - {obj.instrument.symbol}"
        
        for holder in holders:
            user = holder.user
            profile = getattr(user, 'profile', None)
            user_name = profile.full_name if profile and profile.full_name else user.username
            
            message = f"Dear {user_name},\n\n"
            message += "As a shareholder, we know how important it is for you to stay updated on the corporate actions for the stocks you hold. "
            message += "Corporate actions include dividends, bonus shares, stock splits, rights issues, buybacks, mergers, and demergers.\n\n"
            message += "Please find the details of the corporate action(s) for the stock(s) you own:\n\n"
            
            action_name = obj.get_action_type_display()
            # If it's a dividend, we use 'Dividend' as per request template
            if obj.action_type == 'DIVIDEND':
                action_name = "Dividend"
                
            message += f"{action_name} – {obj.instrument.name}\n\n"
            
            ex_date_str = obj.ex_date.strftime('%d-%b-%Y') if obj.ex_date else "–"
            record_date_str = obj.record_date.strftime('%d-%b-%Y') if obj.record_date else "–"
            
            message += f"Ex-date: {ex_date_str}\n"
            message += f"Record Date: {record_date_str}\n\n"
            
            if obj.action_type == 'DIVIDEND':
                rate_val = f"{obj.rate:.0f}" if obj.rate is not None else "–"
                value_val = f"{obj.value:.2f}" if obj.value is not None else "–"
                message += f"Rate*: {rate_val}\n"
                message += f"Value*: {value_val}\n\n"
            elif obj.action_type in ['SPLIT', 'BONUS'] and obj.ratio_numerator:
                message += f"Ratio: {obj.ratio_numerator}:{obj.ratio_denominator}\n\n"
            
            if obj.description:
                message += f"Description: {obj.description}\n\n"
                
            message += "For NCDs/Bonds, the mentioned rate refers to the coupon rate of the security. The value will depend on your holding period."
            
            try:
                if user.email:
                    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
            except Exception as e:
                logger.error(f"Failed to send corporate action email to {user.email}: {e}")

@admin.register(MutualFund)
class MutualFundAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'nav', 'isin', 'amc', 'last_updated')
    search_fields = ('name', 'symbol', 'isin', 'amc')
    list_filter = ('amc',)
    change_list_template = "admin/mf_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('sync-sheet/', self.sync_sheet),
        ]
        return my_urls + urls

    def sync_sheet(self, request):
        from .utils import sync_mutual_funds_from_sheet
        count = sync_mutual_funds_from_sheet()
        if count > 0:
            self.message_user(request, f"Successfully synced {count} Mutual Funds.")
        else:
            self.message_user(request, "Failed to sync Mutual Funds. Check logs.", level=messages.ERROR)
        return redirect("..")

@admin.register(MFPortfolio)
class MFPortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'fund', 'units', 'avg_nav', 'realized_profit')
    search_fields = ('user__username', 'fund__name')
    list_filter = ('user',)

admin.site.register(OTP)
admin.site.register(SignupOTP)

@admin.register(Coin)
class CoinAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'price', 'prev_price', 'last_updated')
    search_fields = ('name', 'symbol')

@admin.register(CoinPortfolio)
class CoinPortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'coin', 'units', 'avg_price', 'realized_profit')
    search_fields = ('user__username', 'coin__name')
    list_filter = ('user',)

@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'coin', 'transaction_type', 'units', 'price', 'date')
    list_filter = ('transaction_type', 'date', 'user')
    search_fields = ('user__username', 'coin__name')

@admin.register(NPSFund)
class NPSFundAdmin(admin.ModelAdmin):
    list_display = ('name', 'nav', 'prev_nav', 'last_updated')
    search_fields = ('name',)

@admin.register(NPSPortfolio)
class NPSPortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'fund', 'units', 'avg_nav', 'realized_profit')
    search_fields = ('user__username', 'fund__name')
    list_filter = ('user',)

@admin.register(NPSTransaction)
class NPSTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'fund', 'transaction_type', 'units', 'price', 'date')
    list_filter = ('transaction_type', 'date', 'user')
    search_fields = ('user__username', 'fund__name')

@admin.register(IPO)
class IPOAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'advise', 'get_status')
    list_filter = ('advise', 'start_date', 'end_date')
    search_fields = ('name', 'company_work')
    ordering = ('-start_date',)

    def get_status(self, obj):
        return obj.status
    get_status.short_description = 'Status'

@admin.register(ChatbotKnowledge)
class ChatbotKnowledgeAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at', 'updated_at')
    search_fields = ('question', 'answer')

@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'is_public', 'created_at')
    list_filter = ('is_public', 'rating', 'created_at')
    search_fields = ('user__username', 'comment')
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_public=True)
    approve_reviews.short_description = "Approve selected reviews (make public)"

    def reject_reviews(self, request, queryset):
        queryset.update(is_public=False)
    reject_reviews.short_description = "Reject selected reviews (hide from public)"
