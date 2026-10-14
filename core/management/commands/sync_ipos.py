import logging
from django.core.management.base import BaseCommand
from core.ipo_sync import auto_sync_foliux_ipos, sync_single_ipo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Auto-check Chittorgarh IPOs & Investorgain GMP, update subscription metrics, GMP reviews one-by-one, 2nd-day APPLY advice, and sync registrar links.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ipo',
            type=str,
            help='Specific IPO name to sync (e.g. "HD Fire Protect" or "Fusion CX")'
        )
        parser.add_argument(
            '--chittorgarh-url',
            type=str,
            help='Specific Chittorgarh URL (detail or /ipo_subscription/ URL)'
        )
        parser.add_argument(
            '--investorgain-url',
            type=str,
            help='Specific Investorgain GMP review URL (e.g. https://www.investorgain.com/gmp/fusion-cx-ipo-gmp/1792/)'
        )
        parser.add_argument(
            '--one-by-one',
            action='store_true',
            default=True,
            help='Scrape individual Investorgain review pages one-by-one for all active IPOs (default: True)'
        )

    def handle(self, *args, **options):
        ipo_name = options.get('ipo')
        ch_url = options.get('chittorgarh_url')
        ig_url = options.get('investorgain_url')
        one_by_one = options.get('one_by_one', True)

        # Direct single IPO URL sync
        if ch_url or ig_url:
            target = ipo_name or "Target IPO"
            self.stdout.write(f"Syncing individual IPO '{target}' with provided URLs...")
            ipo = sync_single_ipo(ipo_name, chittorgarh_url=ch_url, investorgain_url=ig_url)
            if ipo:
                gmp_safe = ipo.gmp_display.replace('₹', 'Rs. ')
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully updated '{ipo.name}': "
                    f"Subscription={ipo.subscription_display}, "
                    f"GMP={gmp_safe}, "
                    f"Advise={ipo.advise}"
                ))
            else:
                self.stderr.write(self.style.ERROR(f"Could not find or update IPO '{target}'"))
            return

        self.stdout.write("Starting Foliux IPO Auto-Sync from Chittorgarh & Investorgain...")
        try:
            stats = auto_sync_foliux_ipos(target_ipo_name=ipo_name, one_by_one=one_by_one)
            self.stdout.write(self.style.SUCCESS(
                f"Foliux IPO Auto-Sync completed.\n"
                f"Added: {stats['added']}, Updated: {stats['updated']}, "
                f"Subscription Enriched: {stats.get('subscription_enriched', 0)}, "
                f"GMP Enriched: {stats.get('gmp_enriched', 0)}, "
                f"Registrar Linked: {stats['registrar_linked']}, "
                f"Skipped Closed: {stats['skipped_closed']}"
            ))
        except Exception as e:
            logger.error(f"Error executing sync_ipos command: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"Failed to sync Foliux IPOs: {e}"))
