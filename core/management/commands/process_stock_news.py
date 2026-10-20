import imaplib
import email
from email.header import decode_header
import datetime
import pytz
import re
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs, unquote

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError

from core.models import Instrument, NewsAlert, Portfolio, EmailLog


class HTMLTextExtractor(HTMLParser):
    """Simple HTML to plain text converter for email bodies without external dependencies."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_text(self):
        return ' '.join(self.text)


def html_to_text(html_content):
    try:
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        return parser.get_text()
    except Exception:
        # Fallback to simple regex tag stripping
        return re.sub(r'<[^>]+>', ' ', html_content)


def normalize_alphanumeric(text):
    """Strips all non-alphanumeric characters and converts to uppercase."""
    return re.sub(r'[^A-Z0-9]', '', str(text).upper())


class Command(BaseCommand):
    help = 'Fetches stock & ETF news alerts from Gmail and sends consolidated updates to relevant users.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Fetch and simulate alerts without sending emails or writing to EmailLog.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Send consolidated alert even if EmailLog says an email was already sent today.'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Send consolidated alert only to a specific user email.'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Number of lookback days for Gmail IMAP and news selection (default: 2 days to cover weekends).'
        )
        parser.add_argument(
            '--fetch-only',
            action='store_true',
            help='Only fetch news from Gmail and save to DB, do not send user emails.'
        )
        parser.add_argument(
            '--send-only',
            action='store_true',
            help='Only send user emails using existing DB news, do not fetch from Gmail.'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        target_email = options.get('email')
        days = options.get('days', 2)
        fetch_only = options.get('fetch_only', False)
        send_only = options.get('send_only', False)

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY-RUN mode. No emails will be sent."))

        # 1. Fetch News from Gmail
        if not send_only:
            self.stdout.write(f"Starting Gmail stock & ETF news fetch (lookback: {days} days)...")
            new_alerts = self.fetch_emails(days=days)
            self.stdout.write(self.style.SUCCESS(f"Fetched and stored {len(new_alerts)} new news items."))
        else:
            self.stdout.write("Skipping Gmail fetch (--send-only requested).")

        # 2. Consolidate and Send Alerts
        if not fetch_only:
            self.stdout.write("Consolidating news alerts by user portfolio...")
            self.send_consolidated_alerts(days=days, dry_run=dry_run, force=force, target_email=target_email)
        else:
            self.stdout.write("Skipping user alert dispatch (--fetch-only requested).")

        self.stdout.write(self.style.SUCCESS("Process completed successfully."))

    def _decode_header_value(self, header_raw):
        """Properly decodes multi-part RFC 2047 MIME headers."""
        if not header_raw:
            return ""
        try:
            parts = decode_header(header_raw)
            decoded = ""
            for text, enc in parts:
                if isinstance(text, bytes):
                    decoded += text.decode(enc or 'utf-8', errors='ignore')
                else:
                    decoded += str(text)
            return decoded.strip()
        except Exception:
            return str(header_raw).strip()

    def fetch_emails(self, days=2):
        imap_url = getattr(settings, 'IMAP_HOST', 'imap.gmail.com')
        user = settings.EMAIL_HOST_USER
        password = (settings.EMAIL_HOST_PASSWORD or '').replace(' ', '')

        if not user or not password:
            self.stderr.write("EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is not set. Cannot connect to Gmail.")
            return []

        try:
            mail = imaplib.IMAP4_SSL(imap_url)
            mail.login(user, password)
            mail.select("inbox")
        except Exception as e:
            self.stderr.write(f"Failed to connect to Gmail ({user}): {str(e)}")
            return []

        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(ist)
        start_dt = now - datetime.timedelta(days=days)
        start_str = start_dt.strftime('%d-%b-%Y')
        end_str = (now + datetime.timedelta(days=1)).strftime('%d-%b-%Y')

        # Primary IMAP search using SENTSINCE / SENTBEFORE
        search_query = f'(SENTSINCE {start_str} SENTBEFORE {end_str})'
        status, messages = mail.search(None, search_query)
        if status != 'OK' or not messages or not messages[0]:
            # Fallback to standard SINCE
            status, messages = mail.search(None, f'(SINCE {start_str})')

        if status != 'OK' or not messages or not messages[0]:
            self.stdout.write(f"No messages found in Gmail for the last {days} days.")
            mail.logout()
            return []

        email_ids = messages[0].split()
        self.stdout.write(f"Found {len(email_ids)} emails in Gmail search window.")
        new_alerts = []

        # Load instruments and pre-build lookup indices
        instruments = list(Instrument.objects.all())
        matcher = InstrumentMatcher(instruments)

        for e_id in email_ids:
            try:
                status, data = mail.fetch(e_id, '(RFC822)')
                if status != 'OK' or not data or not data[0]:
                    continue

                msg = email.message_from_bytes(data[0][1])
                message_id = msg.get('Message-ID')
                if not message_id:
                    # Construct pseudo message id from ID and Date
                    message_id = f"foliux_{e_id.decode()}_{msg.get('Date', '')}"

                if NewsAlert.objects.filter(message_id=message_id).exists():
                    continue

                sender = self._decode_header_value(msg.get('From', '')).lower()
                subject = self._decode_header_value(msg.get('Subject', ''))
                subject_lower = subject.lower()

                # Filter out obvious non-alert / bounce messages
                if 'delivery status' in subject_lower or 'failure' in subject_lower:
                    continue
                if 'security alert' in subject_lower or 'welcome' in subject_lower:
                    continue
                if 'google' not in sender and 'alert' not in sender and 'news' not in sender:
                    continue

                # Clean display title (strip "Google Alert - ", tabs, extra spaces)
                display_title = re.sub(r'^Google Alerts?\s*-\s*', '', subject, flags=re.IGNORECASE).strip()
                display_title = display_title.lstrip('\t').strip()

                # Extract email body (plain text preferred, fallback to HTML)
                body = ""
                html_body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if "attachment" in content_disposition:
                            continue
                        if content_type == "text/plain" and not body:
                            body_bytes = part.get_payload(decode=True)
                            if body_bytes:
                                body = body_bytes.decode(errors='ignore')
                        elif content_type == "text/html" and not html_body:
                            html_bytes = part.get_payload(decode=True)
                            if html_bytes:
                                html_body = html_bytes.decode(errors='ignore')
                else:
                    raw_payload = msg.get_payload(decode=True)
                    if raw_payload:
                        text_payload = raw_payload.decode(errors='ignore')
                        if msg.get_content_type() == 'text/html':
                            html_body = text_payload
                        else:
                            body = text_payload

                if not body and html_body:
                    body = html_to_text(html_body)

                # Match Stock or ETF instrument
                found_instrument = matcher.match(subject, display_title, body)

                if found_instrument:
                    news_url = self._extract_news_url(body or html_body)

                    # Clean summary
                    clean_summary = body or display_title
                    clean_summary = re.sub(
                        r'={3,}\s*News\s*-\s*\d+\s*new\s*results\s*for\s*\[.*?\]\s*={3,}',
                        '', clean_summary, flags=re.IGNORECASE
                    )
                    clean_summary = re.sub(
                        rf'Google Alerts?\s*-\s*{re.escape(found_instrument.name)}',
                        '', clean_summary, flags=re.IGNORECASE
                    )
                    clean_summary = re.sub(
                        rf'Google Alerts?\s*-\s*{re.escape(found_instrument.symbol)}',
                        '', clean_summary, flags=re.IGNORECASE
                    )
                    lines = [line.strip() for line in clean_summary.split('\n') if line.strip() and not line.strip().startswith('---')]
                    clean_summary = '\n'.join(lines[:6])

                    # Save NewsAlert
                    alert = NewsAlert.objects.create(
                        instrument=found_instrument,
                        message_id=message_id,
                        title=display_title,
                        summary=clean_summary[:1000],
                        url=news_url,
                        news_date=now.date()
                    )
                    new_alerts.append(alert)
                    self.stdout.write(f"Processed & Saved: [{found_instrument.symbol}] - {display_title}")

            except Exception as e:
                self.stderr.write(f"Error processing email {e_id}: {str(e)}")

        mail.logout()
        return new_alerts

    def _extract_news_url(self, content):
        if not content:
            return None
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        for url in urls:
            if 'google.com/url' in url or 'google.com/alerts/url' in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if 'url' in params:
                    return unquote(params['url'][0])
                if 'q' in params:
                    return unquote(params['q'][0])
                continue
            if 'google.com' not in url:
                return unquote(url)
        return None

    def send_consolidated_alerts(self, days=2, dry_run=False, force=False, target_email=None):
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(ist)
        start_dt = now - datetime.timedelta(days=days)

        # Get news within the lookback window
        recent_news = NewsAlert.objects.filter(
            news_date__gte=start_dt.date(),
            news_date__lte=now.date()
        ).select_related('instrument').order_by('-created_at')

        if not recent_news.exists():
            self.stdout.write("No news items found in the current lookback window.")
            return

        # Map instruments to news items (deduplicated by title)
        news_by_instrument = {}
        for news in recent_news:
            items = news_by_instrument.setdefault(news.instrument_id, [])
            if not any(i.title == news.title for i in items):
                items.append(news)

        self.stdout.write(f"Mapped news for {len(news_by_instrument)} distinct instruments.")

        # Target users
        users = User.objects.filter(is_active=True).distinct()
        if target_email:
            users = users.filter(email__iexact=target_email.strip())
            if not users.exists():
                self.stderr.write(f"Target user with email '{target_email}' not found.")
                return

        today_date = now.date()
        sent_count = 0

        for user in users:
            # Validate user email
            user_email = (user.email or '').strip()
            if not user_email or '@' not in user_email or user_email.endswith('.local') or user_email.endswith('@example.com'):
                continue

            # Check if user holds any of the instruments with news
            user_holdings = Portfolio.objects.filter(user=user, quantity__gt=0).values_list('instrument_id', flat=True)
            relevant_news = []
            for inst_id in user_holdings:
                if inst_id in news_by_instrument:
                    relevant_news.extend(news_by_instrument[inst_id])

            if not relevant_news:
                continue

            # Check EmailLog
            if not force and not dry_run:
                already_sent = EmailLog.objects.filter(
                    user=user,
                    email_type='daily_stock_news',
                    date_sent=today_date
                ).exists()
                if already_sent:
                    self.stdout.write(f"Already sent Daily Stock News Alert to {user_email} for {today_date}. Skipping.")
                    continue

            # Dry-run notification
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DRY-RUN] Would send {len(relevant_news)} news items to {user_email} "
                        f"({[n.instrument.symbol for n in relevant_news[:5]]})"
                    )
                )
                sent_count += 1
                continue

            # Send email
            email_success = self.send_user_email(user, relevant_news)
            if email_success:
                sent_count += 1
                # Record in EmailLog only AFTER email is successfully delivered
                try:
                    EmailLog.objects.get_or_create(
                        user=user,
                        email_type='daily_stock_news',
                        date_sent=today_date
                    )
                except IntegrityError:
                    pass

        self.stdout.write(self.style.SUCCESS(f"Finished sending news alerts. Total emails sent: {sent_count}"))

    def send_user_email(self, user, news_items):
        ist = pytz.timezone('Asia/Kolkata')
        today_formatted = datetime.datetime.now(ist).strftime('%d %b %Y')
        subject = f"Daily Stock News Alert - {today_formatted}"
        site_url = getattr(settings, 'SITE_URL', 'https://foliux.com').rstrip('/')

        content = f"<h2>Portfolio News & Updates</h2>"
        content += f"<p>Hello {user.first_name if user.first_name else user.username}, here are the latest updates for stocks and ETFs you hold:</p>"

        for item in news_items:
            content += f"<div style='margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px;'>"
            content += f"<h3 style='color: #2c3e50; margin-bottom: 5px;'>{item.instrument.symbol}: {item.title}</h3>"
            content += f"<p style='color: #7f8c8d; font-size: 0.9em; line-height: 1.4;'>{item.summary[:450]}...</p>"
            if item.url:
                content += f"<a href='{item.url}' style='display: inline-block; background-color: #3498db; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 0.85em;'>Read Full Story</a>"
            content += "</div>"

        content += f"<div style='margin-top: 30px; border-top: 2px solid #3498db; padding-top: 20px;'>"
        content += f"<p style='font-weight: bold;'>Want to see all updates in one place?</p>"
        content += f"<a href='{site_url}/stock-news/' style='display: inline-block; background-color: #2c3e50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;'>Know More - View All News</a>"
        content += f"</div>"

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
                subject,
                "",  # Plain text body
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=content,
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Sent consolidated alert to {user.email}"))
            return True
        except Exception as e:
            self.stderr.write(f"Failed to send email to {user.email}: {str(e)}")
            return False


class InstrumentMatcher:
    """Fast, multi-tier matcher for Indian stocks and ETFs."""
    def __init__(self, instruments):
        self.instruments = instruments
        self.symbol_map = {}
        self.norm_symbol_map = {}
        self.name_map = {}
        self.norm_name_map = {}
        self.sorted_by_len = sorted(instruments, key=lambda x: len(x.symbol), reverse=True)

        # Well-known ETF and Stock aliases
        self.aliases = {
            'LARSEN AND TOUBRO': 'LT',
            'LARSEN & TOUBRO': 'LT',
            'LARSEN&TOUBRO': 'LT',
            'NIFTY 50 ETF': 'NIFTYBEES',
            'NIFTY ETF': 'NIFTYBEES',
            'NIFTY BEES': 'NIFTYBEES',
            'NIFTYBEES': 'NIFTYBEES',
            'NIPPON INDIA ETF NIFTY BEES': 'NIFTYBEES',
            'BANK BEES': 'BANKBEES',
            'BANKBEES': 'BANKBEES',
            'NIFTY BANK ETF': 'BANKBEES',
            'GOLD BEES': 'GOLDBEES',
            'GOLDBEES': 'GOLDBEES',
            'NIPPON INDIA ETF GOLD BEES': 'GOLDBEES',
            'GOLD ETF': 'GOLDBEES',
            'SILVER BEES': 'SILVERBEES',
            'SILVERBEES': 'SILVERBEES',
            'SILVER ETF': 'SILVERBEES',
            'IT BEES': 'ITBEES',
            'ITBEES': 'ITBEES',
            'NIFTY IT ETF': 'ITBEES',
            'JUNIOR BEES': 'JUNIORBEES',
            'JUNIORBEES': 'JUNIORBEES',
            'NIFTY NEXT 50 ETF': 'JUNIORBEES',
            'AUTO BEES': 'AUTOBEES',
            'AUTOBEES': 'AUTOBEES',
            'PHARMA BEES': 'PHARMABEES',
            'PHARMABEES': 'PHARMABEES',
            'MID150 BEES': 'MID150BEES',
            'MID150BEES': 'MID150BEES',
            'CONSUM BEES': 'CONSUMBEES',
            'CONSUMBEES': 'CONSUMBEES',
            'CPSE ETF': 'CPSEETF',
            'CPSEETF': 'CPSEETF',
            'NASDAQ 100': 'MON100',
            'NASDAQ 100 ETF': 'MON100',
            'MOTILAL OSWAL NASDAQ 100': 'MON100',
            'MOTILAL OSWAL NASDAQ 100 ETF': 'MON100',
            'MON100': 'MON100',
        }

        for inst in instruments:
            sym = inst.symbol.strip().upper()
            self.symbol_map[sym] = inst
            self.norm_symbol_map[normalize_alphanumeric(sym)] = inst

            clean_name = re.sub(
                r'\b(LIMITED|LTD|CORP|CORPORATION|INC|INCORPORATED|PLC|PVT|PRIVATE)\b',
                '', inst.name.upper()
            ).strip()
            if clean_name:
                self.name_map[clean_name] = inst
                self.norm_name_map[normalize_alphanumeric(clean_name)] = inst

    def match(self, subject, display_title, body):
        subj_upper = (display_title or subject).strip().upper()
        subj_norm = normalize_alphanumeric(subj_upper)

        # 1. Alias lookup
        if subj_upper in self.aliases and self.aliases[subj_upper] in self.symbol_map:
            return self.symbol_map[self.aliases[subj_upper]]
        for alias_key, target_sym in self.aliases.items():
            if alias_key in subj_upper and target_sym in self.symbol_map:
                return self.symbol_map[target_sym]

        # 2. Exact symbol lookup
        if subj_upper in self.symbol_map:
            return self.symbol_map[subj_upper]

        # 3. Normalized alphanumeric symbol lookup (e.g. 'NIFTY BEES' -> 'NIFTYBEES')
        if subj_norm in self.norm_symbol_map:
            return self.norm_symbol_map[subj_norm]

        # 4. Exact cleaned company / ETF name
        if subj_upper in self.name_map:
            return self.name_map[subj_upper]

        # 5. Normalized cleaned name
        if subj_norm in self.norm_name_map:
            return self.norm_name_map[subj_norm]

        # 6. Word boundary search in Subject (allows 2+ characters in subject)
        full_subject_upper = subject.upper()
        for inst in self.sorted_by_len:
            sym = inst.symbol.upper()
            if len(sym) >= 2 and re.search(rf'\b{re.escape(sym)}\b', full_subject_upper):
                return inst

            clean_name = re.sub(
                r'\b(LIMITED|LTD|CORP|CORPORATION|INC|INCORPORATED|PLC|PVT|PRIVATE)\b',
                '', inst.name.upper()
            ).strip()
            if len(clean_name) >= 4 and re.search(rf'\b{re.escape(clean_name)}\b', full_subject_upper):
                return inst

        # 7. Word boundary search in Body (allows 3+ characters in body)
        if body:
            body_upper = body.upper()
            for inst in self.sorted_by_len:
                sym = inst.symbol.upper()
                if len(sym) >= 3 and re.search(rf'\b{re.escape(sym)}\b', body_upper):
                    return inst

                clean_name = re.sub(
                    r'\b(LIMITED|LTD|CORP|CORPORATION|INC|INCORPORATED|PLC|PVT|PRIVATE)\b',
                    '', inst.name.upper()
                ).strip()
                if len(clean_name) >= 5 and re.search(rf'\b{re.escape(clean_name)}\b', body_upper):
                    return inst

        return None
