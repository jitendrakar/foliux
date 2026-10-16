import datetime
import pytz
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from core.models import NewsAlert, Instrument, Portfolio
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Send a test news email to the first active user to verify configuration.'

    def handle(self, *args, **options):
        # Get a test user
        user = User.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(self.style.ERROR('No active user found to send test email.'))
            return

        # Build a simple test news item (use latest NewsAlert if exists)
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(ist)
        # Use the same 9am-9am window for consistency
        end_dt = now.replace(hour=9, minute=0, second=0, microsecond=0)
        start_dt = end_dt - datetime.timedelta(days=1)
        news_items = NewsAlert.objects.filter(news_date__gte=start_dt.date(), news_date__lte=end_dt.date())[:3]
        if not news_items:
            self.stdout.write(self.style.WARNING('No news items in the current window; sending generic test email.'))
        subject = f"Foliux: Test News Email - {now.strftime('%d %b %Y')}"
        content = "<h2>Test News Email</h2>"
        if news_items:
            content += "<p>Below are sample news items from the last 24h (9am‑9am) window:</p>"
            for item in news_items:
                content += f"<div style='margin-bottom:15px;'><h3>{item.instrument.symbol}: {item.title}</h3>"
                content += f"<p>{item.summary[:200]}...</p>"
                if item.url:
                    content += f"<a href='{item.url}' style='color:#3498db;'>Read Full Story</a>"
                content += "</div>"
        site_url = getattr(settings, 'SITE_URL', 'https://foliux.com').rstrip('/')
        content += f"<div style='margin-top: 30px; padding: 25px 20px; text-align: center; font-size: 13px; color: #718096; background-color: #f7fafc; border-top: 1px solid #e2e8f0; border-radius: 6px;'>"
        content += f"<p style='margin: 0 0 8px 0; font-weight: 600; color: #4a5568;'>&copy; 2026 FOLIUX &ndash; Investment Tracking System</p>"
        content += f"<p style='margin: 0 0 8px 0;'>Rule-based investing for disciplined wealth creation.</p>"
        content += f"<p style='margin: 0 0 15px 0;'>This is an automated daily summary. To unsubscribe, please update your <a href='{site_url}/profile/edit/' style='color: #4a5568; text-decoration: underline;'>profile settings</a>.</p>"
        content += f"<div style='margin-top: 20px; padding-top: 15px; border-top: 1px solid #e2e8f0;'>"
        content += f"<p style='margin: 0 0 8px 0;'><a href='{site_url}/profile/request-delete/' style='display: inline-block; background-color: #ffffff; color: #dc3545; border: 1px solid #dc3545; padding: 7px 18px; border-radius: 6px; font-weight: 700; font-size: 13px; text-decoration: none;'>Delete My Account</a></p>"
        content += f"<p style='font-size: 11px; color: #a0aec0; margin: 0 auto; max-width: 460px; line-height: 1.4;'>Permanently delete your Foliux account, profile, portfolios, and all associated data. You will no longer be able to access Foliux or recover any of your data.</p>"
        content += f"</div>"
        content += f"</div>"

        try:
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=content,
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Test email sent to {user.email}'))
        except Exception as e:
            self.stderr.write(f'Failed to send test email: {e}')
