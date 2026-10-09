import re
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any, Tuple
from django.utils import timezone
from core.models import IPO
from core.chittorgarh import fetch_chittorgarh_ipos
from core.investorgain import fetch_investorgain_gmp
from core.registrars import registrar_registry

logger = logging.getLogger(__name__)


def clean_company_name(name: str) -> str:
    """Helper to standardize company names for matching & duplicate checks."""
    if not name:
        return ""
    clean = name.strip()
    clean = clean.replace(" IPO", "").replace(" SME", "").replace(" Limited", "").replace(" Ltd.", "").strip()
    clean = re.sub(r'\[.*?\]', '', clean).strip()
    return clean.lower()


def auto_sync_foliux_ipos() -> Dict[str, Any]:
    """
    Complete Foliux IPO Workflow Engine:
    1. Scrapes Upcoming & Ongoing IPOs from Chittorgarh & Investorgain (Live GMP).
    2. Auto-adds upcoming/current IPOs to Foliux Admin with live GMP and metrics.
    3. Prevents duplicates and retains historical data permanently in database.
    4. Sets initial advise = 'WAITING'.
    5. On 2nd day of subscription (today == start_date + 1 day), sets advise = 'APPLY'
       only when Subscription >= 3x AND GMP > 30%. Otherwise advise = 'WAITING'.
    6. Updates ongoing IPO subscription & GMP metrics.
    7. Synchronizes dynamic registrar data (MUFG, KFintech, etc.).
    """
    today = timezone.localdate()
    logger.info(f"Starting Foliux IPO Auto-Sync Workflow for date: {today}")

    stats = {
        'added': 0,
        'updated': 0,
        'skipped_future': 0,
        'skipped_closed': 0,
        'skipped_duplicate': 0,
        'registrar_linked': 0,
        'gmp_enriched': 0,
    }

    try:
        scraped_ipos = fetch_chittorgarh_ipos()
        logger.info(f"Fetched {len(scraped_ipos)} IPO entries from Chittorgarh.")

        try:
            investorgain_gmp = fetch_investorgain_gmp()
            logger.info(f"Fetched {len(investorgain_gmp)} live GMP entries from Investorgain.")
        except Exception as ex:
            logger.warning(f"Could not fetch Investorgain GMP: {ex}")
            investorgain_gmp = {}

        for item in scraped_ipos:
            name = item.get('name', '').strip()
            start_date = item.get('start_date')
            end_date = item.get('end_date')

            if not name or not start_date:
                continue

            clean_name = clean_company_name(name)
            simple_name = re.sub(r'[^a-z0-9]', '', clean_name)

            # Check if Investorgain has live GMP for this IPO
            ig_data = investorgain_gmp.get(clean_name) or investorgain_gmp.get(simple_name)
            if ig_data:
                if item.get('gmp_amount') is None and ig_data.get('gmp_amount') is not None:
                    item['gmp_amount'] = ig_data['gmp_amount']
                if item.get('gmp_percent') is None and ig_data.get('gmp_percent') is not None:
                    item['gmp_percent'] = ig_data['gmp_percent']

            # Skip only IPOs closed more than 30 days ago
            cutoff_closed = today - timedelta(days=30)
            if end_date and end_date < cutoff_closed:
                stats['skipped_closed'] += 1
                continue

            # Duplicate Check: Check if IPO already exists in Foliux
            existing_ipo = IPO.objects.filter(name__icontains=clean_name).first()
            if not existing_ipo and item.get('symbol'):
                existing_ipo = IPO.objects.filter(symbol__iexact=item['symbol'].strip()).first()

            if not existing_ipo:
                # Auto-add upcoming and current active IPOs to Foliux
                calculated_end_date = end_date or (start_date + timedelta(days=3))
                display_name = re.sub(r'\s+IPO$', '', name, flags=re.I).strip()
                new_ipo = IPO.objects.create(
                    name=display_name,
                    symbol=item.get('symbol') or "",
                    start_date=start_date,
                    end_date=calculated_end_date,
                    company_work=item.get('company_work') or f"{name} Initial Public Offering.",
                    notes=item.get('notes') or "Source: Chittorgarh & Investorgain",
                    advise='WAITING',  # Initial Advise = Waiting
                    registrar_slug=item.get('registrar_slug') or 'mufg',
                    subscription_times=item.get('subscription_times'),
                    gmp_percent=item.get('gmp_percent'),
                    gmp_amount=item.get('gmp_amount'),
                    is_active=True
                )
                stats['added'] += 1
                logger.info(f"Added new IPO to Foliux Admin: '{new_ipo.name}' (Start: {start_date})")
            else:
                # Update existing IPO metrics (upcoming, current, or recent)
                updated_fields = False
                
                if item.get('subscription_times') is not None:
                    existing_ipo.subscription_times = item['subscription_times']
                    updated_fields = True
                if item.get('gmp_percent') is not None:
                    existing_ipo.gmp_percent = item['gmp_percent']
                    updated_fields = True
                if item.get('gmp_amount') is not None:
                    existing_ipo.gmp_amount = item['gmp_amount']
                    updated_fields = True
                # If database existing_ipo still lacks GMP, enrich from Investorgain
                if (existing_ipo.gmp_amount is None or existing_ipo.gmp_percent is None) and ig_data:
                    if existing_ipo.gmp_amount is None and ig_data.get('gmp_amount') is not None:
                        existing_ipo.gmp_amount = ig_data['gmp_amount']
                        updated_fields = True
                    if existing_ipo.gmp_percent is None and ig_data.get('gmp_percent') is not None:
                        existing_ipo.gmp_percent = ig_data['gmp_percent']
                        updated_fields = True

                if item.get('notes') and (not existing_ipo.notes or len(existing_ipo.notes) < 50):
                    existing_ipo.notes = item['notes']
                    updated_fields = True
                if item.get('company_work') and (not existing_ipo.company_work or existing_ipo.company_work.endswith("Initial Public Offering.")):
                    existing_ipo.company_work = item['company_work']
                    updated_fields = True
                if end_date and existing_ipo.end_date != end_date:
                    existing_ipo.end_date = end_date
                    updated_fields = True

                # Rule: 2nd Day Status Update Rule
                # On the 2nd day of subscription (today == start_date + 1 day):
                # Set Advise = APPLY only if Subscription >= 3x AND GMP > 30%. Otherwise WAITING.
                is_second_day = (today == (existing_ipo.start_date + timedelta(days=1)))
                
                sub = float(existing_ipo.subscription_times or 0)
                gmp = float(existing_ipo.gmp_percent or 0)

                if is_second_day:
                    if sub >= 3.0 and gmp > 30.0:
                        if existing_ipo.advise != 'APPLY':
                            existing_ipo.advise = 'APPLY'
                            updated_fields = True
                            logger.info(f"IPO '{existing_ipo.name}' updated to APPLY on 2nd day (Sub: {sub}x, GMP: {gmp}%)")
                    else:
                        if existing_ipo.advise != 'WAITING':
                            existing_ipo.advise = 'WAITING'
                            updated_fields = True
                            logger.info(f"IPO '{existing_ipo.name}' set to WAITING on 2nd day (Sub: {sub}x, GMP: {gmp}%)")

                if updated_fields:
                    existing_ipo.save()
                    stats['updated'] += 1

        # Enrich any active database IPOs with missing GMP from Investorgain
        if investorgain_gmp:
            db_ipos = IPO.objects.filter(is_active=True)
            for db_ipo in db_ipos:
                if db_ipo.gmp_amount is None or db_ipo.gmp_percent is None:
                    c_name = clean_company_name(db_ipo.name)
                    s_name = re.sub(r'[^a-z0-9]', '', c_name)
                    match = investorgain_gmp.get(c_name) or investorgain_gmp.get(s_name)
                    if match:
                        save_req = False
                        if db_ipo.gmp_amount is None and match.get('gmp_amount') is not None:
                            db_ipo.gmp_amount = match['gmp_amount']
                            save_req = True
                        if db_ipo.gmp_percent is None and match.get('gmp_percent') is not None:
                            db_ipo.gmp_percent = match['gmp_percent']
                            save_req = True
                        if save_req:
                            db_ipo.save()
                            stats['gmp_enriched'] += 1
                            logger.info(f"Enriched database IPO '{db_ipo.name}' with Investorgain GMP: {db_ipo.gmp_display}")

        # Registrar Dynamic Synchronization
        try:
            active_registrar_ipos = registrar_registry.get_all_active_ipos()
            for reg_item in active_registrar_ipos:
                reg_slug = reg_item.get('registrar', 'mufg')
                comp_id = str(reg_item.get('id', ''))
                comp_name = reg_item.get('name', '').strip()

                if not comp_id or not comp_name:
                    continue

                clean_search = clean_company_name(comp_name)
                matching_ipo = IPO.objects.filter(name__icontains=clean_search).first()
                if matching_ipo:
                    if matching_ipo.registrar_company_id != comp_id or matching_ipo.registrar_slug != reg_slug or not matching_ipo.is_synced_from_registrar:
                        matching_ipo.registrar_slug = reg_slug
                        matching_ipo.registrar_company_id = comp_id
                        matching_ipo.is_synced_from_registrar = True
                        if matching_ipo.advise == 'WAITING':
                            matching_ipo.is_active = True
                        matching_ipo.save()
                        stats['registrar_linked'] += 1
                        logger.info(f"Synced registrar {reg_slug}:{comp_id} to Foliux IPO '{matching_ipo.name}'")
        except Exception as e:
            logger.error(f"Error during registrar sync: {e}")

    except Exception as e:
        logger.error(f"Error in auto_sync_foliux_ipos workflow: {e}", exc_info=True)

    logger.info(f"Completed Foliux IPO Auto-Sync: {stats}")
    return stats
