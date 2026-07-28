import logging
from django.core.management.base import BaseCommand
from core.models import IPO
from core.registrars import registrar_registry

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronize dynamic IPO IDs from registrars to existing Admin IPO cards (does not auto-create cards)'

    def handle(self, *args, **options):
        self.stdout.write("Starting IPO linking from registrars...")
        
        try:
            active_items = registrar_registry.get_all_active_ipos()
            self.stdout.write(f"Fetched {len(active_items)} active IPOs from registrars.")

            linked_count = 0
            for item in active_items:
                reg_slug = item.get('registrar', 'mufg')
                comp_id = str(item.get('id', ''))
                comp_name = item.get('name', '').strip()

                if not comp_id or not comp_name:
                    continue

                # Find existing Admin-created IPO by name
                clean_search = comp_name.replace(" IPO", "").replace(" SME", "").strip()
                ipo = IPO.objects.filter(name__icontains=clean_search).first()
                if ipo and (ipo.registrar_company_id != comp_id or ipo.registrar_slug != reg_slug):
                    ipo.registrar_slug = reg_slug
                    ipo.registrar_company_id = comp_id
                    ipo.save()
                    linked_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Linked Admin IPO '{ipo.name}' to {reg_slug}:{comp_id}"))

            self.stdout.write(self.style.SUCCESS(f"IPO linking completed. Linked {linked_count} admin cards."))

        except Exception as e:
            logger.error(f"Error executing sync_ipos command: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"Failed to link IPOs: {e}"))
