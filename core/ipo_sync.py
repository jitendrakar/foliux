import re
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone
from core.models import IPO
from core.chittorgarh import fetch_chittorgarh_ipos, scrape_chittorgarh_subscription
from core.investorgain import fetch_investorgain_gmp, scrape_investorgain_gmp_detail, match_investorgain_record
from core.registrars import registrar_registry

logger = logging.getLogger(__name__)


def clean_company_name(name: str) -> str:
    """Helper to standardize company names for matching & duplicate checks."""
    if not name:
        return ""
    clean = name.strip()
    clean = clean.replace(" IPO", "").replace(" SME", "").replace(" Limited", "").replace(" Ltd.", "").strip()
    clean = re.sub(r'\[.*?\]|\(.*?\)', '', clean).strip()
    return clean.lower()


def sync_single_ipo(
    ipo_obj_or_name: Any,
    chittorgarh_url: Optional[str] = None,
    investorgain_url: Optional[str] = None
) -> Optional[IPO]:
    """
    Directly updates a single IPO in Foliux with live Chittorgarh subscription data
    and/or Investorgain GMP review data from specified URLs.
    """
    if isinstance(ipo_obj_or_name, IPO):
        ipo = ipo_obj_or_name
    else:
        c_name = clean_company_name(str(ipo_obj_or_name))
        ipo = IPO.objects.filter(name__icontains=c_name).first()
        if not ipo:
            s_name = re.sub(r'[^a-z0-9]', '', c_name)
            for cand in IPO.objects.filter(is_active=True):
                if s_name and s_name in re.sub(r'[^a-z0-9]', '', cand.name.lower()):
                    ipo = cand
                    break

    if not ipo:
        logger.warning(f"Could not find IPO matching: '{ipo_obj_or_name}'")
        return None

    updated = False

    # 1. Update from Chittorgarh subscription URL
    if chittorgarh_url:
        sub_url = chittorgarh_url.strip()
        if '/ipo/' in sub_url and '/ipo_subscription/' not in sub_url:
            sub_url = re.sub(r'/ipo/', '/ipo_subscription/', sub_url)
        try:
            sub_val = scrape_chittorgarh_subscription(sub_url)
            if sub_val is not None:
                ipo.subscription_times = sub_val
                updated = True
                logger.info(f"Updated '{ipo.name}' subscription from Chittorgarh: {sub_val}x")
        except Exception as e:
            logger.warning(f"Error scraping Chittorgarh subscription for '{ipo.name}': {e}")

    # 2. Update from Investorgain GMP review URL
    if investorgain_url:
        try:
            detail = scrape_investorgain_gmp_detail(investorgain_url.strip())
            if detail:
                if detail.get('gmp_amount') is not None:
                    ipo.gmp_amount = detail['gmp_amount']
                    updated = True
                if detail.get('gmp_percent') is not None:
                    ipo.gmp_percent = detail['gmp_percent']
                    updated = True
                if detail.get('subscription_times') is not None and (ipo.subscription_times is None or ipo.subscription_times == 0):
                    ipo.subscription_times = detail['subscription_times']
                    updated = True
                logger.info(f"Updated '{ipo.name}' GMP from Investorgain: {ipo.gmp_display}")
        except Exception as e:
            logger.warning(f"Error scraping Investorgain GMP for '{ipo.name}': {e}")

    if updated:
        ipo.save()

    return ipo


def auto_sync_foliux_ipos(
    target_ipo_name: Optional[str] = None,
    one_by_one: bool = True
) -> Dict[str, Any]:
    """
    Complete Foliux IPO Workflow Engine:
    1. Scrapes Upcoming & Ongoing IPOs from Chittorgarh (including individual live subscription).
    2. Fetches live Grey Market Premium (GMP) data from Investorgain.
    3. Auto-adds upcoming/current IPOs to Foliux with live GMP, subscription multipliers, and dates.
    4. Enriches active database IPOs with live GMP and subscription metrics one-by-one.
    5. Evaluates 2nd day advice: sets advise = 'APPLY' if Subscription >= 3x AND GMP > 30%, else 'WAITING'.
    6. Synchronizes dynamic registrar data (MUFG, KFintech, etc.).
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
        'subscription_enriched': 0,
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

        # 1. Process scraped Chittorgarh IPOs
        for item in scraped_ipos:
            name = item.get('name', '').strip()
            start_date = item.get('start_date')
            end_date = item.get('end_date')

            if not name or not start_date:
                continue

            clean_name = clean_company_name(name)

            # Match with Investorgain
            ig_match = match_investorgain_record(name, investorgain_gmp)
            if ig_match:
                if item.get('gmp_amount') is None and ig_match.get('gmp_amount') is not None:
                    item['gmp_amount'] = ig_match['gmp_amount']
                if item.get('gmp_percent') is None and ig_match.get('gmp_percent') is not None:
                    item['gmp_percent'] = ig_match['gmp_percent']
                if item.get('subscription_times') is None and ig_match.get('subscription_times') is not None:
                    item['subscription_times'] = ig_match['subscription_times']

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
                calculated_end_date = end_date or (start_date + timedelta(days=3))
                display_name = re.sub(r'\s+IPO$', '', name, flags=re.I).strip()
                new_ipo = IPO.objects.create(
                    name=display_name,
                    symbol=item.get('symbol') or "",
                    start_date=start_date,
                    end_date=calculated_end_date,
                    company_work=item.get('company_work') or f"{name} Initial Public Offering.",
                    notes=item.get('notes') or "Source: Chittorgarh & Investorgain",
                    advise='WAITING',
                    registrar_slug=item.get('registrar_slug') or 'mufg',
                    subscription_times=item.get('subscription_times'),
                    gmp_percent=item.get('gmp_percent'),
                    gmp_amount=item.get('gmp_amount'),
                    is_active=True
                )
                stats['added'] += 1
                logger.info(f"Added new IPO to Foliux Admin: '{new_ipo.name}' (Start: {start_date}, Sub: {new_ipo.subscription_display}, GMP: {new_ipo.gmp_display})")
            else:
                updated_fields = False

                if item.get('subscription_times') is not None and existing_ipo.subscription_times != item['subscription_times']:
                    existing_ipo.subscription_times = item['subscription_times']
                    updated_fields = True
                    stats['subscription_enriched'] += 1

                if item.get('gmp_percent') is not None and existing_ipo.gmp_percent != item['gmp_percent']:
                    existing_ipo.gmp_percent = item['gmp_percent']
                    updated_fields = True

                if item.get('gmp_amount') is not None and existing_ipo.gmp_amount != item['gmp_amount']:
                    existing_ipo.gmp_amount = item['gmp_amount']
                    updated_fields = True

                if (existing_ipo.gmp_amount is None or existing_ipo.gmp_percent is None) and ig_match:
                    if existing_ipo.gmp_amount is None and ig_match.get('gmp_amount') is not None:
                        existing_ipo.gmp_amount = ig_match['gmp_amount']
                        updated_fields = True
                    if existing_ipo.gmp_percent is None and ig_match.get('gmp_percent') is not None:
                        existing_ipo.gmp_percent = ig_match['gmp_percent']
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

                # 2nd Day Advice Rule
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

        # 2. Enrich active database IPOs one by one
        active_ipos_qs = IPO.objects.filter(is_active=True)
        if target_ipo_name:
            active_ipos_qs = active_ipos_qs.filter(name__icontains=clean_company_name(target_ipo_name))

        for db_ipo in active_ipos_qs:
            db_updated = False
            ig_match = match_investorgain_record(db_ipo.name, investorgain_gmp)

            if ig_match:
                # One-by-one detail review scrape for high accuracy
                detail_data = None
                if one_by_one and ig_match.get('url'):
                    try:
                        detail_data = scrape_investorgain_gmp_detail(ig_match['url'])
                    except Exception as e:
                        logger.warning(f"Error scraping individual Investorgain review for '{db_ipo.name}': {e}")

                source_data = detail_data if detail_data else ig_match

                # Update GMP amount & percent
                if source_data.get('gmp_amount') is not None and db_ipo.gmp_amount != source_data['gmp_amount']:
                    db_ipo.gmp_amount = source_data['gmp_amount']
                    db_updated = True
                    stats['gmp_enriched'] += 1

                if source_data.get('gmp_percent') is not None and db_ipo.gmp_percent != source_data['gmp_percent']:
                    db_ipo.gmp_percent = source_data['gmp_percent']
                    db_updated = True

                # Update subscription from Investorgain if missing in DB
                if (db_ipo.subscription_times is None or db_ipo.subscription_times == 0) and source_data.get('subscription_times') is not None:
                    db_ipo.subscription_times = source_data['subscription_times']
                    db_updated = True
                    stats['subscription_enriched'] += 1

            # If subscription is still missing, try to fetch from Chittorgarh
            if db_ipo.subscription_times is None or db_ipo.subscription_times == 0:
                # Look for matching Chittorgarh item
                for ch_item in scraped_ipos:
                    if clean_company_name(ch_item.get('name', '')) in clean_company_name(db_ipo.name) or clean_company_name(db_ipo.name) in clean_company_name(ch_item.get('name', '')):
                        if ch_item.get('subscription_times'):
                            db_ipo.subscription_times = ch_item['subscription_times']
                            db_updated = True
                            stats['subscription_enriched'] += 1
                            break
                        elif ch_item.get('url'):
                            sub_url = ch_item['url'].replace('/ipo/', '/ipo_subscription/')
                            try:
                                sub_val = scrape_chittorgarh_subscription(sub_url)
                                if sub_val is not None:
                                    db_ipo.subscription_times = sub_val
                                    db_updated = True
                                    stats['subscription_enriched'] += 1
                                    break
                            except Exception:
                                pass

            # Re-evaluate 2nd day advice
            is_second_day = (today == (db_ipo.start_date + timedelta(days=1)))
            sub = float(db_ipo.subscription_times or 0)
            gmp = float(db_ipo.gmp_percent or 0)
            if is_second_day:
                if sub >= 3.0 and gmp > 30.0 and db_ipo.advise != 'APPLY':
                    db_ipo.advise = 'APPLY'
                    db_updated = True
                elif (sub < 3.0 or gmp <= 30.0) and db_ipo.advise == 'APPLY':
                    db_ipo.advise = 'WAITING'
                    db_updated = True

            if db_updated:
                db_ipo.save()
                stats['updated'] += 1
                logger.info(f"Updated database IPO '{db_ipo.name}' (Sub: {db_ipo.subscription_display}, GMP: {db_ipo.gmp_display})")

        # 3. Registrar Dynamic Synchronization
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
