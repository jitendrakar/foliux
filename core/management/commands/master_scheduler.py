import pytz
from django.core.management.base import BaseCommand
from django.core import management
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

class Command(BaseCommand):
    help = 'Master scheduler for Foliux daily and periodic tasks.'

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=pytz.timezone('Asia/Kolkata'))
        
        # 1. Sync tasks (every 5 / 30 mins)
        def scheduled_sync():
            self.stdout.write("Running scheduled gsheet sync...")
            try:
                from core.utils import perform_sync
                perform_sync()
            except Exception as e:
                self.stderr.write(f"Error running perform_sync: {e}")

        def scheduled_update_ltp():
            self.stdout.write("Running scheduled update_ltp (force_fetch)...")
            try:
                management.call_command('update_ltp')
            except Exception as e:
                self.stderr.write(f"Error running update_ltp: {e}")

        def scheduled_mf():
            self.stdout.write("Running scheduled mutual fund update...")
            try:
                from core.views import _auto_update_mf
                _auto_update_mf()
            except Exception as e:
                self.stderr.write(f"Error running _auto_update_mf: {e}")

        def scheduled_coin():
            self.stdout.write("Running scheduled coin update...")
            try:
                from core.views import _auto_update_coin
                _auto_update_coin()
            except Exception as e:
                self.stderr.write(f"Error running _auto_update_coin: {e}")

        def scheduled_nps():
            self.stdout.write("Running scheduled NPS update...")
            try:
                from core.views import _auto_update_nps
                _auto_update_nps()
            except Exception as e:
                self.stderr.write(f"Error running _auto_update_nps: {e}")

        def scheduled_rss():
            self.stdout.write("Running scheduled RSS feed cache update...")
            try:
                from core.views import fetch_landing_data
                fetch_landing_data(force_fetch=True)
            except Exception as e:
                self.stderr.write(f"Error running fetch_landing_data: {e}")

        def run_alerts():
            self.stdout.write("Running scheduled signal alerts...")
            try:
                management.call_command('send_signal_alerts')
            except Exception as e:
                self.stderr.write(f"Error running signal alerts: {e}")

        def run_stock_news():
            self.stdout.write("Running scheduled stock news...")
            try:
                management.call_command('process_stock_news')
            except Exception as e:
                self.stderr.write(f"Error running stock news: {e}")

        def run_daily_summary():
            self.stdout.write("Running scheduled daily summary...")
            try:
                management.call_command('send_daily_summary')
            except Exception as e:
                self.stderr.write(f"Error running daily summary: {e}")

        # Add jobs
        scheduler.add_job(scheduled_sync, 'interval', minutes=5, id='gsheet_sync_job')
        scheduler.add_job(scheduled_update_ltp, 'interval', minutes=5, id='update_ltp_job')
        scheduler.add_job(scheduled_rss, 'interval', minutes=30, id='rss_sync_job')
        
        scheduler.add_job(scheduled_mf, 'interval', minutes=30, id='auto_update_mf')
        scheduler.add_job(scheduled_coin, 'interval', minutes=30, id='auto_update_coin')
        scheduler.add_job(scheduled_nps, 'interval', minutes=30, id='auto_update_nps')
        
        scheduler.add_job(run_alerts, 'interval', minutes=15, id='send_signal_alerts')
        
        # Daily cron jobs (9:00 AM & 10:00 AM IST)
        scheduler.add_job(run_stock_news, CronTrigger(hour=9, minute=0), id='daily_stock_news_job', misfire_grace_time=3600)
        scheduler.add_job(run_daily_summary, CronTrigger(hour=10, minute=0), id='daily_portfolio_summary_job', misfire_grace_time=3600)
        
        self.stdout.write("Starting BlockingScheduler (timezone: Asia/Kolkata)...")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write("BlockingScheduler stopped.")
