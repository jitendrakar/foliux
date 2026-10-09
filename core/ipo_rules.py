import re
import datetime
import pytz
from django.utils import timezone
from core.models import IPO

def extract_ipo_metrics(ipo):
    """
    Extracts total Subscription multiple (e.g. 7.56) and GMP percentage (e.g. 37.0)
    from IPO fields (notes, company_work, advise).
    """
    text = f"{ipo.notes or ''}\n{ipo.company_work or ''}\n{ipo.advise or ''}"
    
    # 1. Extract Subscription multiple (e.g. "7.56x", "Subscribed 8.89 times", "Subscription: 3.5x", "3.5 times")
    sub_val = None
    sub_matches = re.findall(r'(?:subscription|subscribed|sub)\D*?(\d+(?:\.\d+)?)\s*(?:x|times)?', text, re.IGNORECASE)
    if sub_matches:
        for m in sub_matches:
            try:
                val = float(m)
                if 0.1 <= val <= 500.0:  # reasonable subscription multiple range
                    sub_val = val
                    break
            except ValueError:
                pass

    # 2. Extract GMP percentage (e.g. "GMP: 37%", "Listing Gain: 37%", "Expected Listing Gain: 17.06%")
    gmp_val = None
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
    On closing day at or after 10:00 AM IST:
      Set Advise = APPLY only when:
        Subscription >= 3x AND GMP > 30%
      Otherwise set Advise = NON_APPLY (or WAITING if incomplete).
    """
    kolkata_tz = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(kolkata_tz)
    today_ist = now_ist.date()
    current_hour = now_ist.hour

    ipos_to_check = [ipo] if ipo else IPO.objects.filter(is_active=True)
    results = []

    for item in ipos_to_check:
        # Check if today is closing day (or force=True)
        is_closing_day = (today_ist == item.end_date)
        is_after_10am = (current_hour >= 10)

        if not (is_closing_day and is_after_10am) and not force:
            results.append({
                'ipo_id': item.id,
                'name': item.name,
                'status': 'SKIPPED',
                'reason': f"Not closing day or before 10 AM (Closing Date: {item.end_date}, Today: {today_ist}, Hour: {current_hour})"
            })
            continue

        sub, gmp = extract_ipo_metrics(item)
        
        # Check rule: Subscription >= 3x AND GMP > 30%
        sub_passed = (sub is not None and sub >= 3.0)
        gmp_passed = (gmp is not None and gmp > 30.0)

        old_advise = item.advise
        
        if sub_passed and gmp_passed:
            new_advise = 'APPLY'
            rule_note = f"\n\n🤖 Automated Closing Day Evaluation (10:00 AM IST):\nRating updated to APPLY.\nReason: Subscription ({sub:.2f}x) >= 3x AND GMP ({gmp:.1f}%) > 30% on closing day."
        else:
            new_advise = 'NON_APPLY'
            reasons = []
            if sub is None or sub < 3.0:
                reasons.append(f"Subscription ({sub if sub is not None else 'N/A'}) < 3x")
            if gmp is None or gmp <= 30.0:
                reasons.append(f"GMP ({f'{gmp:.1f}%' if gmp is not None else 'N/A'}) <= 30%")
            rule_note = f"\n\n🤖 Automated Closing Day Evaluation (10:00 AM IST):\nRating updated to NON_APPLY.\nReason: {', '.join(reasons)} on closing day."

        item.advise = new_advise
        
        # Append rule evaluation note if not already present
        if "Automated Closing Day Evaluation" not in (item.notes or ""):
            item.notes = (item.notes or "").strip() + rule_note
            
        item.save()
        
        results.append({
            'ipo_id': item.id,
            'name': item.name,
            'status': 'UPDATED',
            'old_advise': old_advise,
            'new_advise': new_advise,
            'subscription': sub,
            'gmp_percent': gmp,
            'rule_passed': (sub_passed and gmp_passed)
        })

    return results
