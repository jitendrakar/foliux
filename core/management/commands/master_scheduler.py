import time
import datetime
import pytz
from django.core.management.base import BaseCommand
from django.core import management

class Command(BaseCommand):
    help = 'Master scheduler for Foliux daily and periodic tasks.'

    def handle(self, *args, **options):
        ist = pytz.timezone('Asia/Kolkata')
        self.stdout.write("Master Scheduler Started (IST Timezone).")
        self.stdout.write("- 9:00 AM : process_stock_news (News Alerts)")
        self.stdout.write("- 10:00 AM : send_daily_summary (Portfolio Snapshot)")
        self.stdout.write("- Every 15 mins : send_signal_alerts (Instant Signal Changes)")
        
        last_signal_run = None
        
        while True:
            now = datetime.datetime.now(ist)
            
            # 1. Check for 9:00 AM task (process_stock_news)
            if now.hour == 9 and now.minute == 0:
                self.stdout.write(f"[{now.strftime('%H:%M:%S')}] Running process_stock_news...")
                try:
                    management.call_command('process_stock_news')
                except Exception as e:
                    self.stderr.write(f"Error running process_stock_news: {e}")
                time.sleep(60) # Sleep 60s to prevent double execution in the same minute
                continue
                
            # 2. Check for 10:00 AM task (send_daily_summary)
            if now.hour == 10 and now.minute == 0:
                self.stdout.write(f"[{now.strftime('%H:%M:%S')}] Running send_daily_summary...")
                try:
                    management.call_command('send_daily_summary')
                except Exception as e:
                    self.stderr.write(f"Error running send_daily_summary: {e}")
                time.sleep(60) # Sleep 60s to prevent double execution in the same minute
                continue

            # 3. Check for instant alerts (run every 15 minutes)
            if last_signal_run is None or (now - last_signal_run).total_seconds() >= 900: # 900 seconds = 15 mins
                self.stdout.write(f"[{now.strftime('%H:%M:%S')}] Running send_signal_alerts...")
                try:
                    management.call_command('send_signal_alerts')
                except Exception as e:
                    self.stderr.write(f"Error running send_signal_alerts: {e}")
                last_signal_run = datetime.datetime.now(ist)
                
            # Sleep 30 seconds before checking the time again
            time.sleep(30)
