from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from core.models import SignalNotificationState
from core.utils import get_recommendations, get_portfolio_summary_metrics
import logging

from django.db import transaction

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Checks portfolio signal counts and sends styled email alerts to users if their counts have changed.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sending emails even if signal counts haven\'t changed',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        users = User.objects.filter(is_active=True)
        emails_sent = 0
        
        for user in users:
            try:
                if not hasattr(user, 'profile') or not user.email:
                    continue  # Skip users without profiles or emails

                # Use a transaction and select_for_update to prevent duplicate processing by multiple workers
                with transaction.atomic():
                    # Get Current Metrics via consolidated utility
                    metrics = get_portfolio_summary_metrics(user)
                    current_buy = metrics['buy_count']
                    current_reduce = metrics['reduce_count']
                    current_sell = metrics['sell_count']
                    total_current = metrics['total_count']

                    # Get or Create Notification State and Lock it
                    state, created = SignalNotificationState.objects.select_for_update().get_or_create(
                        user=user,
                        defaults={
                            'last_buy_count': current_buy,
                            'last_reduce_count': current_reduce,
                            'last_sell_count': current_sell
                        }
                    )

                    # Has anything changed?
                    has_changed = (
                        state.last_buy_count != current_buy or 
                        state.last_reduce_count != current_reduce or 
                        state.last_sell_count != current_sell
                    )

                    if (has_changed or force) and total_current > 0:
                        # Prepare Email Template
                        subject = f"Alert: Portfolio Signal Change Detected - {timezone.now().strftime('%d %b %Y')}"
                        site_url = getattr(settings, 'SITE_URL', 'https://foliux.com')
                        
                        context = {
                            'user': user,
                            'today': timezone.now(),
                            'portfolio_value': metrics['portfolio_value'],
                            'initial_capital': metrics['initial_capital'],
                            'unrealized_pnl': metrics['unrealized_pnl'],
                            'total_realized': metrics['total_realized'],
                            'liabilities': metrics['liabilities'],
                            'buy_count': current_buy,
                            'reduce_count': current_reduce,
                            'sell_count': current_sell,
                            'total_count': total_current,
                            'site_url': site_url
                        }

                        html_message = render_to_string('emails/daily_portfolio_summary.html', context)
                        plain_message = strip_tags(html_message)

                        # Update State Tracking IMMEDIATELY inside the transaction
                        # This ensures other workers see the update before we even spend time sending the mail
                        state.last_buy_count = current_buy
                        state.last_reduce_count = current_reduce
                        state.last_sell_count = current_sell
                        state.save()

                        # Send Email
                        # If send_mail fails, the transaction will rollback, resetting the state counts
                        # and allowing a retry (or the next worker) to process it.
                        send_mail(
                            subject=subject,
                            message=plain_message,
                            from_email=f"FOLIUX <{settings.EMAIL_HOST_USER}>",
                            recipient_list=[user.email],
                            html_message=html_message,
                            fail_silently=False,
                        )

                        emails_sent += 1
                        self.stdout.write(self.style.SUCCESS(f'Successfully sent signal alert to {user.email}'))
                    
            except Exception as e:
                logger.error(f"Failed to process signal alerts for {user.username}: {e}")
                self.stdout.write(self.style.ERROR(f'Error processing user {user.username}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Completed processing. Emails sent: {emails_sent}'))
