from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import os
        import sys
        from django.core.management import call_command

        # Avoid starting the scheduler when running management commands (like migrate, check, etc.)
        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'check', 'shell', 'test']):
            return

        def run_alerts():
            try:
                call_command('send_signal_alerts')
            except Exception as e:
                print(f"Error running signal alerts: {e}")

        def run_stock_news():
            try:
                call_command('process_stock_news')
            except Exception as e:
                print(f"Error running stock news: {e}")

        def run_daily_summary():
            try:
                call_command('send_daily_summary')
            except Exception as e:
                print(f"Error running daily summary: {e}")

        # Helper to avoid heavy imports at startup
        def scheduled_sync():
            from .utils import perform_sync
            perform_sync()

        def scheduled_mf():
            from .views import _auto_update_mf
            _auto_update_mf()

        def scheduled_coin():
            from .views import _auto_update_coin
            _auto_update_coin()

        def scheduled_nps():
            from .views import _auto_update_nps
            _auto_update_nps()

        # Ensure scheduler runs in appropriate environments
        is_manage_py = 'manage.py' in sys.argv[0]
        is_runserver = 'runserver' in sys.argv
        is_main_process = os.environ.get('RUN_MAIN') == 'true'
        is_gunicorn = os.environ.get('SERVER_SOFTWARE', '').startswith('gunicorn')
        is_iis = os.environ.get('SERVER_SOFTWARE', '').startswith('Microsoft-IIS') or os.environ.get('WSGI_HANDLER')

        # Only run scheduler in local runserver mode (to make local development easy).
        # In production (Gunicorn, IIS, etc.), the scheduler should run as a separate
        # background process via 'python manage.py master_scheduler'.
        if is_runserver and is_main_process:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            scheduler = BackgroundScheduler()

            # --- Existing interval jobs ---
            scheduler.add_job(scheduled_sync, 'interval', minutes=5, id='gsheet_sync_job', replace_existing=True)
            scheduler.add_job(scheduled_mf, 'interval', minutes=30, id='auto_update_mf', replace_existing=True)
            scheduler.add_job(scheduled_coin, 'interval', minutes=30, id='auto_update_coin', replace_existing=True)
            scheduler.add_job(scheduled_nps, 'interval', minutes=30, id='auto_update_nps', replace_existing=True)

            # --- Daily Email Jobs (previously in master_scheduler) ---

            # 9:00 AM IST — Daily Stock News Alert
            scheduler.add_job(
                run_stock_news,
                CronTrigger(hour=9, minute=0, timezone='Asia/Kolkata'),
                id='daily_stock_news_job',
                replace_existing=True,
                misfire_grace_time=3600  # Fire up to 1 hour late if process was restarting
            )

            # 10:00 AM IST — Daily Portfolio Summary
            scheduler.add_job(
                run_daily_summary,
                CronTrigger(hour=10, minute=0, timezone='Asia/Kolkata'),
                id='daily_portfolio_summary_job',
                replace_existing=True,
                misfire_grace_time=3600
            )

            # 4:00 PM IST — Daily Signal Alerts
            scheduler.add_job(
                run_alerts,
                CronTrigger(hour=16, minute=0, timezone='Asia/Kolkata'),
                id='daily_signal_alerts_job',
                replace_existing=True,
                misfire_grace_time=3600
            )

            try:
                print("Starting background scheduler...")
                scheduler.start()
                print(f"Background scheduler started (Env: {'IIS' if is_iis else 'Other'}) with auto updates + daily emails.")
                print("  - 09:00 AM IST: Daily Stock News Alert")
                print("  - 10:00 AM IST: Daily Portfolio Summary")
                print("  - 04:00 PM IST: Daily Signal Alerts")
            except Exception as e:
                print(f"Failed to start scheduler: {e}")
