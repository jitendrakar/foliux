from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from core.utils import get_recommendations, record_portfolio_value_history, get_portfolio_summary_metrics
from core.models import Portfolio, MFPortfolio, CoinPortfolio, NPSPortfolio, Loan, FixedAsset, OtherAsset, PnLStatement
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Send daily summary to a specific user email only',
        )

    def handle(self, *args, **options):
        email_filter = options.get('email')
        if email_filter:
            users = User.objects.filter(email=email_filter, is_active=True)
        else:
            users = User.objects.filter(is_active=True)
            
        emails_sent = 0
        today = timezone.now()
        
        self.stdout.write(f"Starting daily summary email process for {users.count()} users...")

        for user in users:
            try:
                if not hasattr(user, 'profile') or not user.email:
                    continue

                # 1. Update Portfolio History (Ensure fresh data)
                record_portfolio_value_history(user)
                
                # 2. Get Portfolio Metrics (and Signals)
                metrics = get_portfolio_summary_metrics(user)

                # 3. Send Email
                subject = f"Your Daily Portfolio Summary - {today.strftime('%d %b %Y')}"
                site_url = getattr(settings, 'SITE_URL', 'https://foliux.com')
                
                context = {
                    'user': user,
                    'today': today,
                    'portfolio_value': metrics['portfolio_value'],
                    'initial_capital': metrics['initial_capital'],
                    'unrealized_pnl': metrics['unrealized_pnl'],
                    'total_realized': metrics['total_realized'],
                    'liabilities': metrics['liabilities'],
                    'buy_count': metrics['buy_count'],
                    'reduce_count': metrics['reduce_count'],
                    'sell_count': metrics['sell_count'],
                    'total_count': metrics['total_count'],
                    'site_url': site_url
                }

                html_message = render_to_string('emails/daily_portfolio_summary.html', context)
                plain_message = strip_tags(html_message)

                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                emails_sent += 1
                self.stdout.write(self.style.SUCCESS(f'Sent daily summary to {user.email}'))

            except Exception as e:
                logger.error(f"Failed to send daily summary to {user.username}: {e}")
                self.stdout.write(self.style.ERROR(f'Error processing user {user.username}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Finished. Sent {emails_sent} emails.'))
