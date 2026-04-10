from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import os
        from django.core.management import call_command
        
        def run_alerts():
            try:
                call_command('send_signal_alerts')
            except Exception as e:
                print(f"Error running signal alerts: {e}")

        # Ensure scheduler only runs once in the main process
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('SERVER_SOFTWARE', '').startswith('gunicorn'):
            from .utils import perform_sync
            from .views import _auto_update_mf, _auto_update_coin, _auto_update_nps
            from apscheduler.schedulers.background import BackgroundScheduler
            
            scheduler = BackgroundScheduler()
            scheduler.add_job(perform_sync, 'interval', minutes=5, id='gsheet_sync_job', replace_existing=True)
            scheduler.add_job(_auto_update_mf, 'interval', minutes=30, id='auto_update_mf', replace_existing=True)
            scheduler.add_job(_auto_update_coin, 'interval', minutes=30, id='auto_update_coin', replace_existing=True)
            scheduler.add_job(_auto_update_nps, 'interval', minutes=30, id='auto_update_nps', replace_existing=True)
            scheduler.add_job(run_alerts, 'cron', hour=10, minute=0, id='daily_signal_alerts', replace_existing=True)
            scheduler.start()
            print("Background scheduler started for sync and auto updates (5m interval).")
        elif not os.environ.get('RUN_MAIN'):
            # Fallback for other environments like IIS
            from .utils import perform_sync
            from .views import _auto_update_mf, _auto_update_coin, _auto_update_nps
            from apscheduler.schedulers.background import BackgroundScheduler
            
            scheduler = BackgroundScheduler()
            scheduler.add_job(perform_sync, 'interval', minutes=5, id='gsheet_sync_job', replace_existing=True)
            scheduler.add_job(_auto_update_mf, 'interval', minutes=30, id='auto_update_mf', replace_existing=True)
            scheduler.add_job(_auto_update_coin, 'interval', minutes=30, id='auto_update_coin', replace_existing=True)
            scheduler.add_job(_auto_update_nps, 'interval', minutes=30, id='auto_update_nps', replace_existing=True)
            scheduler.add_job(run_alerts, 'cron', hour=10, minute=0, id='daily_signal_alerts_iis', replace_existing=True)
            scheduler.start()
            print("Background scheduler started (IIS/Generic) with auto updates (5m interval).")
