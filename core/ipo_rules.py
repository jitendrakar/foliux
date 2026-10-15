import re
import datetime
import pytz
from django.utils import timezone
from core.models import IPO

def extract_ipo_metrics(ipo):
    """
    Extracts total Subscription multiple (e.g. 7.56) and GMP percentage (e.g. 37.0)
    from IPO model fields first, falling back to text fields (notes, company_work).
    """
    # 1. Primary Source: Check dedicated database model fields
    sub_val = None
    if ipo.subscription_times is not None:
        try:
            val = float(ipo.subscription_times)
            if 0.0 <= val <= 1000.0:
                sub_val = val
        except (ValueError, TypeError):
            pass

    gmp_val = None
    if ipo.gmp_percent is not None:
        try:
            val = float(ipo.gmp_percent)
            if -100.0 <= val <= 2000.0:
                gmp_val = val
        except (ValueError, TypeError):
            pass

    # 2. Secondary Fallback: Extract from text fields if either metric is missing
    if sub_val is None or gmp_val is None:
        # Strip previous automated notes to avoid matching stale text
        raw_notes = re.sub(r'🤖 Automated (?:Closing Day|Bidding) Evaluation.*', '', ipo.notes or '', flags=re.DOTALL)
        text = f"{raw_notes}\n{ipo.company_work or ''}"

        if sub_val is None:
            sub_matches = re.findall(r'(?:subscription|subscribed|sub)\D*?(\d+(?:\.\d+)?)\s*(?:x|times)?', text, re.IGNORECASE)
            if sub_matches:
                for m in sub_matches:
                    try:
                        val = float(m)
                        if 0.1 <= val <= 500.0:
                            sub_val = val
                            break
                    except ValueError:
                        pass

        if gmp_val is None:
            gmp_matches = re.findall(r'(?:gmp|listing gain|gain)\D*?(\d+(?:\.\d+)?)\s*%', text, re.IGNORECASE)
            if gmp_matches:
                for m in gmp_matches:
                    try:
                        val = float(m)
                        if 0.0 <= val <= 500.0:
                            gmp_val = val
                            break
                    except ValueError:
                        pass

    return sub_val, gmp_val

def evaluate_closing_day_ipo_advice(ipo=None, force=False):
    """
    Evaluates IPO advice rule:
    - On closing day (at or after 10:00 AM IST) OR for past closed IPOs:
        Set Advise = APPLY only when:
          Subscription >= 3x AND GMP > 30%
        Otherwise set Advise = NON_APPLY.
    - During active bidding (Day 2 onwards until closing day morning):
        Set Advise = APPLY if Subscription >= 3x AND GMP > 30%
        Otherwise keep Advise = WAITING.
    """
    kolkata_tz = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(kolkata_tz)
    today_ist = now_ist.date()
    current_hour = now_ist.hour

    ipos_to_check = [ipo] if ipo else IPO.objects.filter(is_active=True)
    results = []

    for item in ipos_to_check:
        is_closing_day = (today_ist == item.end_date)
        is_past_closed = (today_ist > item.end_date)
        is_after_10am = (current_hour >= 10)
        is_active_bidding = (item.start_date < today_ist < item.end_date) or (is_closing_day and not is_after_10am)

        # Decide eligibility
        is_final_evaluation = is_past_closed or (is_closing_day and is_after_10am)

        if not is_final_evaluation and not is_active_bidding and not force:
            results.append({
                'ipo_id': item.id,
                'name': item.name,
                'status': 'SKIPPED',
                'reason': f"Upcoming IPO or not ready for evaluation (Dates: {item.start_date} to {item.end_date}, Today: {today_ist})"
            })
            continue

        sub, gmp = extract_ipo_metrics(item)
        
        # Check rule: Subscription >= 3x AND GMP > 30%
        sub_passed = (sub is not None and sub >= 3.0)
        gmp_passed = (gmp is not None and gmp > 30.0)
        rule_passed = (sub_passed and gmp_passed)

        old_advise = item.advise

        if is_final_evaluation or force:
            if rule_passed:
                new_advise = 'APPLY'
                rule_note = f"\n\n🤖 Automated Closing Day Evaluation:\nRating updated to APPLY.\nReason: Subscription ({sub:.2f}x) >= 3x AND GMP ({gmp:.1f}%) > 30% on closing day."
            else:
                new_advise = 'NON_APPLY'
                reasons = []
                if sub is None or sub < 3.0:
                    reasons.append(f"Subscription ({f'{sub:.2f}x' if sub is not None else 'N/A'}) < 3x")
                if gmp is None or gmp <= 30.0:
                    reasons.append(f"GMP ({f'{gmp:.1f}%' if gmp is not None else 'N/A'}) <= 30%")
                rule_note = f"\n\n🤖 Automated Closing Day Evaluation:\nRating updated to NON_APPLY.\nReason: {', '.join(reasons)} on closing day."
        else:
            # During active bidding window before closing day 10 AM
            if rule_passed:
                new_advise = 'APPLY'
                rule_note = f"\n\n🤖 Automated Bidding Evaluation:\nRating updated to APPLY.\nReason: Subscription ({sub:.2f}x) >= 3x AND GMP ({gmp:.1f}%) > 30% during open bidding."
            else:
                new_advise = 'WAITING'
                rule_note = None

        item.advise = new_advise

        # Update note: replace any prior automated note cleanly
        if rule_note:
            cleaned_notes = re.sub(r'\n*🤖 Automated (?:Closing Day|Bidding) Evaluation.*', '', item.notes or '', flags=re.DOTALL).strip()
            item.notes = f"{cleaned_notes}{rule_note}" if cleaned_notes else rule_note.strip()
            
        item.save()
        
        results.append({
            'ipo_id': item.id,
            'name': item.name,
            'status': 'UPDATED',
            'old_advise': old_advise,
            'new_advise': new_advise,
            'subscription': sub,
            'gmp_percent': gmp,
            'rule_passed': rule_passed
        })

    return results
