import imaplib
import email
from email.header import decode_header
import datetime
import pytz
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from core.models import Instrument, NewsAlert, Portfolio
from django.contrib.auth.models import User
from django.db.models import Q
from decimal import Decimal

class Command(BaseCommand):
    help = 'Fetches stock news alerts from Gmail and sends consolidated updates to relevant users.'

    def handle(self, *args, **options):
        self.stdout.write("Starting stock news process...")
        
        # 1. Fetch News from Gmail
        new_alerts = self.fetch_emails()
        self.stdout.write(f"Fetched {len(new_alerts)} new news items.")

        # 2. Consolidate and Send Alerts
        self.send_consolidated_alerts()
        
        self.stdout.write("Process completed.")

    def fetch_emails(self):
        import re
        # Gmail IMAP settings
        imap_url = 'imap.gmail.com'
        user = settings.EMAIL_HOST_USER
        password = settings.EMAIL_HOST_PASSWORD # App Password

        # Connect to Gmail
        try:
            mail = imaplib.IMAP4_SSL(imap_url)
            mail.login(user, password)
            mail.select("inbox")
        except Exception as e:
            self.stderr.write(f"Failed to connect to Gmail: {str(e)}")
            return []

        # IST Timezone
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.datetime.now(ist).date()
        
        # Search for all emails today from Google Alerts or similar
        # (Optional: Filter by sender for better accuracy)
        # For now, we search all today
        date_str = today.strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SENTSINCE {date_str})')
        
        if status != 'OK':
            self.stdout.write("No messages found for today.")
            return []

        email_ids = messages[0].split()
        new_alerts = []

        # Get all instruments to match symbols
        instruments = Instrument.objects.all()

        for e_id in email_ids:
            try:
                # Fetch the email data
                status, data = mail.fetch(e_id, '(RFC822)')
                if status != 'OK': continue
                
                msg = email.message_from_bytes(data[0][1])
                message_id = msg.get('Message-ID')

                # Check if already processed
                if NewsAlert.objects.filter(message_id=message_id).exists():
                    continue

                # Filter by Sender and Subject
                sender = msg.get('From', '').lower()
                
                # Decode subject
                subject_header = msg.get("Subject", "")
                subject, encoding = decode_header(subject_header)[0]
                if isinstance(subject, bytes):
                    try:
                        subject = subject.decode(encoding if encoding else "utf-8")
                    except Exception:
                        subject = str(subject)
                
                subject_lower = subject.lower()
                
                if 'google' not in sender and 'alert' not in sender:
                    continue
                
                if 'security alert' in subject_lower or 'welcome' in subject_lower:
                    continue


                # Strip "Google Alert - " from subject
                display_title = re.sub(r'^Google Alert\s*-\s*', '', subject, flags=re.IGNORECASE)

                # Get body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            body_bytes = part.get_payload(decode=True)
                            if body_bytes:
                                body = body_bytes.decode(errors='ignore')
                            break
                else:
                    body_bytes = msg.get_payload(decode=True)
                    if body_bytes:
                        body = body_bytes.decode(errors='ignore')

                # Extraction Logic: Find Stock Name/Symbol in subject or body
                found_instrument = self.extract_instrument(subject, body, instruments)
                
                if found_instrument:
                    # Extract URL from body
                    from urllib.parse import urlparse, parse_qs, unquote
                    
                    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
                    news_url = None
                    for url in urls:
                        # If it's a Google redirection link, try to extract the real destination
                        if 'google.com/url' in url or 'google.com/alerts/url' in url:
                            parsed = urlparse(url)
                            params = parse_qs(parsed.query)
                            # Google Alerts usually use 'url' or 'q' for the destination
                            if 'url' in params:
                                news_url = params['url'][0]
                                break
                            elif 'q' in params:
                                news_url = params['q'][0]
                                break
                            continue # Keep looking if we couldn't parse it
                            
                        if 'google.com' not in url:
                            news_url = url
                            break
                    
                    # Unquote the URL just in case it's still encoded
                    if news_url:
                        news_url = unquote(news_url)

                    # Clean the Summary (Body)
                    # 1. Remove Google Alert header markers (e.g., === News - 10 new results for [Reliance] ===)
                    clean_summary = re.sub(r'={3,}\s*News\s*-\s*\d+\s*new\s*results\s*for\s*\[.*?\]\s*={3,}', '', body, flags=re.IGNORECASE)
                    # 2. Remove "Google Alert - [Stock Name]"
                    clean_summary = re.sub(rf'Google Alert\s*-\s*{re.escape(found_instrument.name)}', '', clean_summary, flags=re.IGNORECASE)
                    clean_summary = re.sub(rf'Google Alert\s*-\s*{re.escape(found_instrument.symbol)}', '', clean_summary, flags=re.IGNORECASE)
                    # 3. Strip leading/trailing lines that are empty or contain only junk
                    lines = [line.strip() for line in clean_summary.split('\n') if line.strip() and not line.strip().startswith('---')]
                    clean_summary = '\n'.join(lines[:5]) # Keep first 5 meaningful lines

                    # Save NewsAlert
                    alert = NewsAlert.objects.create(
                        instrument=found_instrument,
                        message_id=message_id,
                        title=display_title,
                        summary=clean_summary[:1000],
                        url=news_url,
                        alert_type="News",
                        news_date=today
                    )

                    new_alerts.append(alert)

                    self.stdout.write(f"Processed: {found_instrument.symbol} - {display_title}")


            except Exception as e:
                self.stderr.write(f"Error processing email {e_id}: {str(e)}")

        mail.logout()
        return new_alerts

    def extract_instrument(self, subject, body, instruments):
        import re
        subject_text = subject.upper()
        body_text = body.upper()
        
        # Sort by length descending
        sorted_instruments = sorted(instruments, key=lambda x: len(x.symbol), reverse=True)
        
        # 1. Try to find a match in the SUBJECT first (Highest priority)
        for inst in sorted_instruments:
            if len(inst.symbol) < 3: continue
            
            # Check symbol
            if re.search(rf'\b{re.escape(inst.symbol.upper())}\b', subject_text):
                return inst
            
            # Check name (clean it up first)
            clean_name = re.sub(r'\b(LIMITED|LTD|CORP|CORPORATION|INC|INCORPORATED|PLC|PVT|PRIVATE)\b', '', inst.name.upper()).strip()
            if len(clean_name) > 4 and re.search(rf'\b{re.escape(clean_name)}\b', subject_text):
                return inst
        
        # 2. If no match in subject, try the BODY
        for inst in sorted_instruments:
            if len(inst.symbol) < 3: continue
            
            # Check symbol
            if re.search(rf'\b{re.escape(inst.symbol.upper())}\b', body_text):
                return inst
                
            # Check name
            clean_name = re.sub(r'\b(LIMITED|LTD|CORP|CORPORATION|INC|INCORPORATED|PLC|PVT|PRIVATE)\b', '', inst.name.upper()).strip()
            if len(clean_name) > 4 and re.search(rf'\b{re.escape(clean_name)}\b', body_text):
                return inst
                
        return None





    def send_consolidated_alerts(self):
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.datetime.now(ist).date()

        # Get all news from today that hasn't been sent in a consolidated alert
        # (Assuming we run this command once a day or want to send what's new)
        # For simplicity in this local test, we'll just send all news of today to relevant users.
        
        today_news = NewsAlert.objects.filter(news_date=today)
        if not today_news.exists():
            self.stdout.write("No news to send today.")
            return

        # Map instruments to news
        news_by_instrument = {}
        for news in today_news:
            if news.instrument_id not in news_by_instrument:
                news_by_instrument[news.instrument_id] = []
            news_by_instrument[news.instrument_id].append(news)

        # Get all active users with portfolios
        users = User.objects.filter(is_active=True).distinct()

        for user in users:
            # Find which stocks the user holds
            user_holdings = Portfolio.objects.filter(user=user, quantity__gt=0).values_list('instrument_id', flat=True)
            
            relevant_news = []
            for inst_id in user_holdings:
                if inst_id in news_by_instrument:
                    relevant_news.extend(news_by_instrument[inst_id])

            if relevant_news:
                self.send_user_email(user, relevant_news)

    def send_user_email(self, user, news_items):
        subject = f"Foliux: Daily Stock News Alert - {datetime.date.today().strftime('%d %b %Y')}"
        
        # Create a simple HTML content
        content = f"<h2>Stock Updates for Your Portfolio</h2>"
        content += f"<p>Hello {user.first_name if user.first_name else user.username}, here are the latest updates for stocks you hold:</p>"
        
        for item in news_items:
            content += f"<div style='margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px;'>"
            content += f"<h3 style='color: #2c3e50; margin-bottom: 5px;'>{item.instrument.symbol}: {item.title}</h3>"
            content += f"<p style='color: #7f8c8d; font-size: 0.9em; line-height: 1.4;'>{item.summary[:400]}...</p>"
            if item.url:
                content += f"<a href='{item.url}' style='display: inline-block; background-color: #3498db; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 0.85em;'>Read Full Story</a>"
            content += "</div>"
            
        content += "<p style='font-size: 0.8em; color: #95a5a6; margin-top: 30px;'>This is an automated alert from Foliux.</p>"

        try:
            send_mail(
                subject,
                "", # Plain text body
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=content,
                fail_silently=False,
            )
            self.stdout.write(f"Sent consolidated alert to {user.email}")
        except Exception as e:
            self.stderr.write(f"Failed to send email to {user.email}: {str(e)}")

