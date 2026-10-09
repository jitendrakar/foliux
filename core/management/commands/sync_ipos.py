import logging
from django.core.management.base import BaseCommand
from core.ipo_sync import auto_sync_foliux_ipos

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Auto-check Chittorgarh IPOs, add IPOs starting today to Foliux Admin, update 2nd-day APPLY advice, subscription metrics, and sync registrar links.'

    def handle(self, *args, **options):
        self.stdout.write("Starting Foliux IPO Auto-Sync from Chittorgarh & Registrars...")
        try:
            stats = auto_sync_foliux_ipos()
            self.stdout.write(self.style.SUCCESS(
                f"Foliux IPO Auto-Sync completed. "
                f"Added: {stats['added']}, Updated: {stats['updated']}, "
                f"Registrar Linked: {stats['registrar_linked']}, "
                f"Skipped Future: {stats['skipped_future']}, Skipped Closed: {stats['skipped_closed']}"
            ))
        except Exception as e:
            logger.error(f"Error executing sync_ipos command: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"Failed to sync Foliux IPOs: {e}"))
