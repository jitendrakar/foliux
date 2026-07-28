import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import IPO
from core.registrars import registrar_registry

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronize dynamic IPO listings from all registered registrars (MUFG, etc.)'

    def handle(self, *args, **options):
        self.stdout.write("Starting IPO synchronization from registrars...")
        
        try:
            active_items = registrar_registry.get_all_active_ipos()
            self.stdout.write(f"Fetched {len(active_items)} active IPOs from registrars.")

            today = timezone.localdate()
            synced_ids = set()

            for item in active_items:
                reg_slug = item.get('registrar', 'mufg')
                comp_id = str(item.get('id', ''))
                comp_name = item.get('name', '').strip()

                if not comp_id or not comp_name:
                    continue

                # 1. Try finding by registrar_slug & registrar_company_id
                ipo = IPO.objects.filter(registrar_slug=reg_slug, registrar_company_id=comp_id).first()

                if not ipo:
                    # 2. Try finding by exact name
                    ipo = IPO.objects.filter(name__iexact=comp_name).first()
                    if ipo:
                        ipo.registrar_slug = reg_slug
                        ipo.registrar_company_id = comp_id
                        ipo.is_active = True
                        ipo.save()
                        self.stdout.write(self.style.SUCCESS(f"Linked existing IPO '{comp_name}' to {reg_slug}:{comp_id}"))

                if not ipo:
                    # 3. Create new synced IPO
                    ipo = IPO.objects.create(
                        name=comp_name,
                        start_date=today,
                        end_date=today + timezone.timedelta(days=7),
                        company_work=f"Dynamic IPO listing synchronized from {item.get('registrar_name', 'Registrar')}.",
                        notes="Live allotment status lookup is available for this issue.",
                        advise='WAITING',
                        registrar_slug=reg_slug,
                        registrar_company_id=comp_id,
                        is_synced_from_registrar=True,
                        is_active=True
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created new synced IPO '{comp_name}' ({reg_slug}:{comp_id})"))
                else:
                    # Update active status & name if changed
                    updated = False
                    if ipo.name != comp_name:
                        ipo.name = comp_name
                        updated = True
                    if not ipo.is_active:
                        ipo.is_active = True
                        updated = True
                    if updated:
                        ipo.save()
                        self.stdout.write(f"Updated IPO '{comp_name}'")

                synced_ids.add((reg_slug, comp_id))

            # Mark missing synced IPOs as inactive
            stale_ipos = IPO.objects.filter(is_synced_from_registrar=True, is_active=True)
            stale_count = 0
            for ipo in stale_ipos:
                if (ipo.registrar_slug, ipo.registrar_company_id) not in synced_ids:
                    ipo.is_active = False
                    ipo.save()
                    stale_count += 1

            if stale_count > 0:
                self.stdout.write(f"Marked {stale_count} stale IPOs as inactive.")

            self.stdout.write(self.style.SUCCESS("IPO synchronization completed successfully."))

        except Exception as e:
            logger.error(f"Error executing sync_ipos command: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"Failed to sync IPOs: {e}"))
