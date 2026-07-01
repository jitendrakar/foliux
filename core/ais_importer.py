import json
import base64
import hashlib
import zipfile
import io
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

from .models import (
    IncomeTaxProfile, IncomeTaxTds, IncomeTaxSalary, IncomeTaxInterest,
    IncomeTaxDividend, IncomeTaxEquity, IncomeTaxMutualFund, IncomeTaxSft,
    IncomeTaxTaxPaid, IncomeTaxRefund, IncomeTaxDemand, IncomeTaxOther
)

def _decrypt_with_password(iv, salt, ciphertext, password):
    # Derive 32-byte key using PBKDF2-HMAC-SHA256 with 1000 iterations
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 1000, dklen=32)

    # Decrypt using AES-256-CBC
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Unpad PKCS7
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted.decode('utf-8')


def decrypt_ais_json(file_bytes, password):
    """
    Decrypts the AIS JSON payload.
    Supports:
    1. Plain text JSON (if zip was already extracted by the user).
    2. Password-protected ZIP file (official download format).
    3. Custom encrypted AES-CBC JSON format.
    """
    # 1. Check if it is a ZIP archive
    if file_bytes.startswith(b'PK\x03\x04'):
        try:
            zip_data = io.BytesIO(file_bytes)
            with zipfile.ZipFile(zip_data) as zf:
                json_filenames = [name for name in zf.namelist() if name.lower().endswith('.json')]
                if not json_filenames:
                    raise ValueError("No JSON file found inside the ZIP archive.")
                
                # Try raw, uppercase, and lowercase passwords
                passwords_to_try = [password, password.upper(), password.lower()]
                for pwd in passwords_to_try:
                    try:
                        with zf.open(json_filenames[0], pwd=pwd.encode('utf-8')) as f:
                            return f.read().decode('utf-8', errors='ignore')
                    except Exception:
                        continue
                raise ValueError("Invalid password or corrupted AIS JSON file.")
        except Exception as e:
            if "Invalid password" in str(e):
                raise ValueError("Invalid password or corrupted AIS JSON file.")
            raise ValueError(f"Failed to read ZIP file: {str(e)}")

    # 2. Convert to string for JSON check or AES decryption
    try:
        file_content_str = file_bytes.decode('utf-8', errors='ignore').strip()
    except Exception:
        raise ValueError("Corrupted File.")

    # 3. Check if it is already a plain text JSON
    try:
        json.loads(file_content_str)
        return file_content_str
    except Exception:
        pass

    # 4. Decrypt using AES-256-CBC
    if len(file_content_str) < 64:
        raise ValueError("Invalid password or corrupted AIS JSON file.")
    
    iv_hex = file_content_str[:32]
    salt_hex = file_content_str[32:64]
    ciphertext_str = file_content_str[64:]

    try:
        iv = bytes.fromhex(iv_hex)
        salt = bytes.fromhex(salt_hex)
    except Exception as e:
        raise ValueError("Invalid password or corrupted AIS JSON file.")

    # Decode ciphertext (Try base64, fallback to hex)
    # Strip any whitespace/newlines that may have been introduced during file upload
    ciphertext_str_clean = ciphertext_str.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    try:
        ciphertext = base64.b64decode(ciphertext_str_clean)
    except Exception:
        try:
            ciphertext = bytes.fromhex(ciphertext_str_clean)
        except Exception:
            raise ValueError("Invalid password or corrupted AIS JSON file.")

    # Try raw, uppercase, and lowercase password variants, including the secret middle segment "GQ39%*g"
    passwords_to_try = [password]
    if password.upper() not in passwords_to_try:
        passwords_to_try.append(password.upper())
    if password.lower() not in passwords_to_try:
        passwords_to_try.append(password.lower())

    # Generate candidates with the middle segment "GQ39%*g"
    candidates_with_middle = []
    for pwd in passwords_to_try:
        if len(pwd) == 18:
            pan = pwd[:10]
            dob = pwd[10:]
            candidates_with_middle.append(f"{pan.lower()}GQ39%*g{dob}")
            candidates_with_middle.append(f"{pan.upper()}GQ39%*g{dob}")
        elif len(pwd) > 10:
            pan = pwd[:10]
            rest = pwd[10:]
            candidates_with_middle.append(f"{pan.lower()}GQ39%*g{rest}")
            candidates_with_middle.append(f"{pan.upper()}GQ39%*g{rest}")

    for cand in candidates_with_middle:
        if cand not in passwords_to_try:
            passwords_to_try.append(cand)

    for pwd in passwords_to_try:
        try:
            return _decrypt_with_password(iv, salt, ciphertext, pwd)
        except Exception:
            continue

    raise ValueError("Invalid password or corrupted AIS JSON file.")




def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(val):
    if val is None:
        return Decimal('0')
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    val_str = str(val).replace(',', '').strip()
    try:
        return Decimal(val_str)
    except Exception:
        return Decimal('0')


def find_key_case_insensitive(data, search_key):
    """Recursively search for a key in a dictionary (case-insensitive) and return its value."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == search_key.lower():
                return v
            res = find_key_case_insensitive(v, search_key)
            if res is not None:
                return res
    elif isinstance(data, list):
        for item in data:
            res = find_key_case_insensitive(item, search_key)
            if res is not None:
                return res
    return None


def find_all_lists_matching_key(data, search_key_sub):
    """Recursively find lists that are under keys containing search_key_sub."""
    results = []
    if isinstance(data, dict):
        for k, v in data.items():
            if search_key_sub.lower() in k.lower() and isinstance(v, list):
                results.extend(v)
            else:
                results.extend(find_all_lists_matching_key(v, search_key_sub))
    elif isinstance(data, list):
        for item in data:
            results.extend(find_all_lists_matching_key(item, search_key_sub))
    return results



def parse_and_import_ais(user, decrypted_text, financial_year, duplicate_action='replace'):
    """
    Parses the decrypted AIS JSON and imports it.
    Returns: (summary_dict, error_message)
    """
    try:
        data = json.loads(decrypted_text)
    except Exception:
        return None, "Invalid JSON structure."

    # Validate version/signature (Basic AIS validation)
    has_part_a = find_key_case_insensitive(data, 'partA') is not None
    has_part_b = find_key_case_insensitive(data, 'partB') is not None
    if not (has_part_a or has_part_b or 'alldata' in data or 'pan' in str(data).lower()):
        return None, "Unsupported AIS Version or invalid AIS structure."

    # Extract Part A (Profile)
    part_a_data = extract_part_a_profile(data)
    if not part_a_data.get('pan'):
        return None, "Missing Mandatory Fields: PAN is not found in the AIS file."

    # If duplicate action is not specified, check if records already exist
    existing_profile = IncomeTaxProfile.objects.filter(user=user, financial_year=financial_year).first()
    if existing_profile and not duplicate_action:
        return {'status': 'duplicate_detected', 'financial_year': financial_year}, None

    # Handle Duplicate Actions
    if existing_profile and duplicate_action == 'replace':
        # Delete existing data for this financial year
        IncomeTaxProfile.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxTds.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxSalary.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxInterest.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxDividend.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxEquity.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxMutualFund.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxSft.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxTaxPaid.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxRefund.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxDemand.objects.filter(user=user, financial_year=financial_year).delete()
        IncomeTaxOther.objects.filter(user=user, financial_year=financial_year).delete()

    imported_on = timezone.now()
    source = 'AIS JSON'
    salary_aggregates = {}

    # Save/Update Profile
    profile_record, created = IncomeTaxProfile.objects.get_or_create(
        user=user,
        financial_year=financial_year,
        defaults={
            'source': source,
            'imported_on': imported_on,
            'json_reference': part_a_data,
            'pan': part_a_data['pan'],
            'aadhaar': part_a_data['aadhaar'],
            'name': part_a_data['name'],
            'dob': part_a_data['dob'],
            'email': part_a_data['email'],
            'mobile': part_a_data['mobile'],
            'address': part_a_data['address'],
        }
    )
    if not created and duplicate_action == 'merge':
        profile_record.pan = part_a_data['pan']
        profile_record.aadhaar = part_a_data['aadhaar']
        profile_record.name = part_a_data['name']
        profile_record.dob = part_a_data['dob']
        profile_record.email = part_a_data['email']
        profile_record.mobile = part_a_data['mobile']
        profile_record.address = part_a_data['address']
        profile_record.json_reference = part_a_data
        profile_record.imported_on = imported_on
        profile_record.save()

    import re

    counts = {
        'salary': 0, 'tds': 0, 'interest': 0, 'dividend': 0,
        'equity': 0, 'mutual_fund': 0, 'sft': 0, 'tax_payment': 0,
        'refund': 0, 'demand': 0, 'other': 0
    }

    def get_field_by_label(row, labels, field_names):
        for idx, lbl in enumerate(labels):
            lbl_name = ""
            if isinstance(lbl, dict):
                lbl_name = lbl.get('name', '') or lbl.get('field', '')
            else:
                lbl_name = str(lbl)
                
            lbl_lower = lbl_name.lower()
            for f in field_names:
                if f.lower() in lbl_lower:
                    if idx < len(row):
                        return row[idx]
        return None

    def parse_source_name_and_id(source_str):
        if not source_str:
            return "", ""
        match = re.search(r'([^(]+)\(([^)]+)\)', source_str)
        if match:
            name = match.group(1).strip()
            id_val = match.group(2).strip()
            return name, id_val
        return source_str.strip(), ""

    part_b = data.get('partB', {})
    sections = part_b.get('sections', []) if isinstance(part_b, dict) else []

    if sections:
        # Walk official sections
        for sec in sections:
            sec_key = sec.get('sectionKey')
            elements = sec.get('elements', [])
            
            for el in elements:
                title = el.get('title', '')
                l2 = el.get('l2', {})
                l1 = el.get('l1', {})
                
                l2_labels = l2.get('columnLabel', [])
                l2_rows = l2.get('columnData', [])
                
                l1_labels = l1.get('columnLabel', [])
                l1_rows = l1.get('columnData', [])
                
                # --- SECTION: tdsTcs ---
                if sec_key == 'tdsTcs':
                    # l2_rows hold one row per deductor/code; l1_rows hold the quarter-level details
                    # We process each l1_row independently (they all belong to the same element/deductor)
                    code = ''
                    deductor_name = ''
                    tan_val = ''
                    info_desc = ''
                    for l2_row in l2_rows:
                        code = get_field_by_label(l2_row, l2_labels, ['code']) or code
                        source_str = get_field_by_label(l2_row, l2_labels, ['source']) or ''
                        info_desc = get_field_by_label(l2_row, l2_labels, ['description', 'desc']) or info_desc
                        if source_str:
                            deductor_name, tan_val = parse_source_name_and_id(source_str)

                    for l1_row in l1_rows:
                        quarter = get_field_by_label(l1_row, l1_labels, ['quarter', 'qtr']) or ''
                        amount_paid = parse_decimal(get_field_by_label(l1_row, l1_labels, ['paid', 'credited', 'amtPaid']))
                        tax_deducted = parse_decimal(get_field_by_label(l1_row, l1_labels, ['deducted', 'amountDeducted']))
                        tax_collected = parse_decimal(get_field_by_label(l1_row, l1_labels, ['collected', 'amountCollected']))

                        if duplicate_action == 'merge':
                            if IncomeTaxTds.objects.filter(user=user, financial_year=financial_year, tan=tan_val, section=code.replace('TDS-', '').replace('TCS-', ''), quarter=quarter, amount_paid=amount_paid, tax_deducted=tax_deducted).exists():
                                continue

                        IncomeTaxTds.objects.create(
                            user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                            deductor_name=deductor_name, tan=tan_val, section=code.replace('TDS-', '').replace('TCS-', ''),
                            amount_paid=amount_paid, tax_deducted=tax_deducted, tax_collected=tax_collected, quarter=quarter
                        )
                        counts['tds'] += 1

                        if '192' in code or 'salary' in title.lower():
                            emp_key = source_str if source_str else deductor_name
                            if not emp_key:
                                emp_key = 'Unknown Employer'
                            
                            suffix = f" - {info_desc}" if info_desc else (f" - {title}" if title else " - Salary received (Section 192)")
                            full_emp_name = f"{emp_key}{suffix}"
                            
                            if full_emp_name not in salary_aggregates:
                                salary_aggregates[full_emp_name] = {
                                    'salary': Decimal('0'),
                                    'perquisites': Decimal('0'),
                                    'tax_deducted': Decimal('0'),
                                    'json_reference': l1_row
                                }
                            salary_aggregates[full_emp_name]['salary'] += amount_paid
                            salary_aggregates[full_emp_name]['tax_deducted'] += tax_deducted
                
                # --- SECTION: sft ---
                elif sec_key == 'sft':
                    for l2_row in l2_rows:
                        code = get_field_by_label(l2_row, l2_labels, ['code']) or ''
                        source_str = get_field_by_label(l2_row, l2_labels, ['source']) or ''
                        source_name, source_id = parse_source_name_and_id(source_str)
                        
                        for l1_row in l1_rows:
                            row_str = str(l1_row)
                            if source_id and source_id not in row_str:
                                continue
                                
                            # 1. Dividends (SFT-015)
                            if '015' in code or '15' in code:
                                amt = parse_decimal(get_field_by_label(l1_row, l1_labels, ['amount', 'amtPaid', 'dividend']))
                                if duplicate_action == 'merge':
                                    if IncomeTaxDividend.objects.filter(user=user, financial_year=financial_year, company_name=source_name, amount=amt).exists():
                                        continue
                                IncomeTaxDividend.objects.create(
                                    user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                                    company_name=source_name, amount=amt
                                )
                                counts['dividend'] += 1
                                
                            # 2. Interest (SFT-016)
                            elif '016' in code or '16' in code:
                                amt = parse_decimal(get_field_by_label(l1_row, l1_labels, ['amount', 'amtPaid', 'interest']))
                                if duplicate_action == 'merge':
                                    if IncomeTaxInterest.objects.filter(user=user, financial_year=financial_year, bank_name=source_name, amount=amt).exists():
                                        continue
                                IncomeTaxInterest.objects.create(
                                    user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                                    bank_name=source_name, interest_type='Savings/FD', amount=amt
                                )
                                counts['interest'] += 1
                                
                            # 3. Mutual Fund (SFT-018)
                            elif '018' in code or '18' in code:
                                amc_name = get_field_by_label(l1_row, l1_labels, ['amc', 'fund', 'amcName', 'fundName']) or source_name
                                scheme_name = get_field_by_label(l1_row, l1_labels, ['scheme', 'schemeName']) or title
                                buy_amt = parse_decimal(get_field_by_label(l1_row, l1_labels, ['purchase', 'totalPurchaseAmount', 'purchaseAmount']))
                                sell_amt = parse_decimal(get_field_by_label(l1_row, l1_labels, ['sales', 'totalSalesValue', 'redemption', 'redeemed']))
                                units_val = parse_decimal(get_field_by_label(l1_row, l1_labels, ['units']))
                                total_amt = buy_amt + sell_amt
                                if duplicate_action == 'merge':
                                    if IncomeTaxMutualFund.objects.filter(user=user, financial_year=financial_year, amc=amc_name, purchase=buy_amt, redemption=sell_amt).exists():
                                        pass
                                    else:
                                        IncomeTaxMutualFund.objects.create(
                                            user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                                            amc=amc_name, scheme=scheme_name, purchase=buy_amt, redemption=sell_amt, units=units_val, amount=total_amt
                                        )
                                        counts['mutual_fund'] += 1
                                else:
                                    IncomeTaxMutualFund.objects.create(
                                        user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                                        amc=amc_name, scheme=scheme_name, purchase=buy_amt, redemption=sell_amt, units=units_val, amount=total_amt
                                    )
                                    counts['mutual_fund'] += 1

                            # 4. Equity (SFT-017)
                            elif '017' in code or '17' in code:
                                buy_amt = parse_decimal(get_field_by_label(l1_row, l1_labels, ['purchase', 'buy', 'marketPurchase', 'purchaseValue']))
                                sell_amt = parse_decimal(get_field_by_label(l1_row, l1_labels, ['sales', 'sell', 'marketSales', 'saleValue']))
                                if duplicate_action == 'merge':
                                    if IncomeTaxEquity.objects.filter(user=user, financial_year=financial_year, broker=source_name, buy_value=buy_amt, sell_value=sell_amt).exists():
                                        pass
                                    else:
                                        IncomeTaxEquity.objects.create(
                                            user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                                            broker=source_name, isin='', buy_value=buy_amt, sell_value=sell_amt
                                        )
                                        counts['equity'] += 1
                                else:
                                    IncomeTaxEquity.objects.create(
                                        user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                                        broker=source_name, isin='', buy_value=buy_amt, sell_value=sell_amt
                                    )
                                    counts['equity'] += 1
                            else:
                                amt = parse_decimal(get_field_by_label(l1_row, l1_labels, ['amount', 'value']))
                                if duplicate_action == 'merge':
                                    if IncomeTaxSft.objects.filter(user=user, financial_year=financial_year, reporting_entity=source_name, description=title, amount=amt).exists():
                                        continue
                                IncomeTaxSft.objects.create(
                                    user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=l1_row,
                                    reporting_entity=source_name, description=title, amount=amt
                                )
                                counts['sft'] += 1
                                
                # --- SECTION: paymentOfTaxes ---
                elif sec_key == 'paymentOfTaxes':
                    el_labels = el.get('columnLabel', [])
                    el_rows = el.get('columnData', [])
                    for el_row in el_rows:
                        tax_type = get_field_by_label(el_row, el_labels, ['minor head', 'major head', 'type']) or 'Tax Payment'
                        bsr_code = get_field_by_label(el_row, el_labels, ['bsr code']) or ''
                        challan_no = get_field_by_label(el_row, el_labels, ['challan serial number', 'challan serial', 'challan identification number']) or ''
                        date_val_str = get_field_by_label(el_row, el_labels, ['date of deposit', 'date']) or ''
                        date_of_payment = parse_date(date_val_str)
                        amount = parse_decimal(get_field_by_label(el_row, el_labels, ['total', 'amount']))
                        
                        if duplicate_action == 'merge':
                            if IncomeTaxTaxPaid.objects.filter(user=user, financial_year=financial_year, challan_number=challan_no, amount=amount).exists():
                                continue
                                
                        IncomeTaxTaxPaid.objects.create(
                            user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=el_row,
                            tax_type=tax_type, bsr_code=bsr_code, challan_number=challan_no, date=date_of_payment, amount=amount
                        )
                        counts['tax_payment'] += 1
                        
                # --- SECTION: demandAndRefund ---
                elif sec_key == 'demandAndRefund':
                    el_labels = el.get('columnLabel', [])
                    el_rows = el.get('columnData', [])
                    is_refund = 'refund' in title.lower() or any('refund' in str(lbl).lower() for lbl in el_labels)
                    
                    for el_row in el_rows:
                        ay = get_field_by_label(el_row, el_labels, ['assessment year', 'ay']) or ''
                        if is_refund:
                            refund_amount = parse_decimal(get_field_by_label(el_row, el_labels, ['refund amount', 'amount']))
                            date_str = get_field_by_label(el_row, el_labels, ['date of refund', 'date']) or ''
                            date_of_refund = parse_date(date_str)
                            refund_mode = get_field_by_label(el_row, el_labels, ['refund mode', 'mode']) or ''
                            
                            if duplicate_action == 'merge':
                                if IncomeTaxRefund.objects.filter(user=user, financial_year=financial_year, assessment_year=ay, refund_amount=refund_amount).exists():
                                    continue
                                    
                            IncomeTaxRefund.objects.create(
                                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=el_row,
                                assessment_year=ay, refund_amount=refund_amount, date=date_of_refund, status=refund_mode or 'Refund Paid'
                            )
                            counts['refund'] += 1
                        else:
                            demand_amount = parse_decimal(get_field_by_label(el_row, el_labels, ['demand amount', 'amount']))
                            section_code = get_field_by_label(el_row, el_labels, ['section']) or ''
                            
                            if duplicate_action == 'merge':
                                if IncomeTaxDemand.objects.filter(user=user, financial_year=financial_year, assessment_year=ay, outstanding_demand=demand_amount).exists():
                                    continue
                                    
                            IncomeTaxDemand.objects.create(
                                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=el_row,
                                assessment_year=ay, outstanding_demand=demand_amount, status=section_code or 'Outstanding'
                            )
                            counts['demand'] += 1

                # --- SECTION: other-info ---
                elif sec_key == 'other-info':
                    for l2_row in l2_rows:
                        code = get_field_by_label(l2_row, l2_labels, ['code']) or ''
                        source_str = get_field_by_label(l2_row, l2_labels, ['source']) or ''
                        source_name, source_id = parse_source_name_and_id(source_str)
                        info_desc = get_field_by_label(l2_row, l2_labels, ['description', 'desc']) or ''
                        
                        for l1_row in l1_rows:
                            row_str = str(l1_row)
                            if source_id and source_id not in row_str:
                                continue
                                
                            if 'SAL' in code or 'salary' in title.lower():
                                gross = parse_decimal(get_field_by_label(l1_row, l1_labels, ['grossSalary', 'gross']))
                                perks = parse_decimal(get_field_by_label(l1_row, l1_labels, ['perquisites', 'valueOfPerquisites172']))
                                
                                emp_key = source_str if source_str else source_name
                                if not emp_key:
                                    emp_key = 'Unknown Employer'
                                
                                suffix = f" - {info_desc}" if info_desc else (f" - {title}" if title else " - Salary (TDS Annexure II)")
                                full_emp_name = f"{emp_key}{suffix}"
                                
                                if full_emp_name not in salary_aggregates:
                                    salary_aggregates[full_emp_name] = {
                                        'salary': gross,
                                        'perquisites': perks,
                                        'tax_deducted': Decimal('0'),
                                        'json_reference': l1_row
                                    }
    else:
        # LEGACY/SIMPLE FALLBACK (uses find_all_lists_matching_key for flat formats)
        tds_entries = find_all_lists_matching_key(data, 'tds') or find_all_lists_matching_key(data, 'tcs')
        sft_entries = find_all_lists_matching_key(data, 'sft') or find_all_lists_matching_key(data, 'transaction')
        tax_payments = find_all_lists_matching_key(data, 'taxPayment') or find_all_lists_matching_key(data, 'taxpaid') or find_all_lists_matching_key(data, 'challan')
        refunds = find_all_lists_matching_key(data, 'refund')
        demands = find_all_lists_matching_key(data, 'demand')
        others = find_all_lists_matching_key(data, 'otherInfo') or find_all_lists_matching_key(data, 'otherInformation')

        # 1. Process TDS Entries
        for entry in tds_entries:
            tan = find_key_case_insensitive(entry, 'tan') or find_key_case_insensitive(entry, 'deductorTan') or ''
            deductor_name = find_key_case_insensitive(entry, 'deductorName') or find_key_case_insensitive(entry, 'partyName') or ''
            section = find_key_case_insensitive(entry, 'section') or find_key_case_insensitive(entry, 'tdsSection') or ''
            amount_paid = parse_decimal(find_key_case_insensitive(entry, 'amountPaid') or find_key_case_insensitive(entry, 'transAmt'))
            tax_deducted = parse_decimal(find_key_case_insensitive(entry, 'taxDeducted') or find_key_case_insensitive(entry, 'tdsAmt'))
            tax_collected = parse_decimal(find_key_case_insensitive(entry, 'taxCollected') or find_key_case_insensitive(entry, 'tcsAmt'))
            quarter = find_key_case_insensitive(entry, 'quarter') or find_key_case_insensitive(entry, 'qtr') or ''

            if duplicate_action == 'merge':
                if IncomeTaxTds.objects.filter(user=user, financial_year=financial_year, tan=tan, section=section, quarter=quarter, amount_paid=amount_paid, tax_deducted=tax_deducted).exists():
                    continue

            IncomeTaxTds.objects.create(
                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                deductor_name=deductor_name, tan=tan, section=section, amount_paid=amount_paid, tax_deducted=tax_deducted,
                tax_collected=tax_collected, quarter=quarter
            )
            counts['tds'] += 1

            if section == '192' or 'salary' in str(entry).lower():
                emp_key = deductor_name or 'Unknown Employer'
                suffix = " - Salary received (Section 192)"
                full_emp_name = f"{emp_key}{suffix}"
                
                if full_emp_name not in salary_aggregates:
                    salary_aggregates[full_emp_name] = {
                        'salary': Decimal('0'),
                        'perquisites': Decimal('0'),
                        'tax_deducted': Decimal('0'),
                        'json_reference': entry
                    }
                salary_aggregates[full_emp_name]['salary'] += amount_paid
                salary_aggregates[full_emp_name]['tax_deducted'] += tax_deducted

        # 2. Process SFT Entries
        for entry in sft_entries:
            reporting_entity = find_key_case_insensitive(entry, 'reportingEntity') or find_key_case_insensitive(entry, 'partyName') or ''
            desc = find_key_case_insensitive(entry, 'description') or find_key_case_insensitive(entry, 'infoDesc') or ''
            amount = parse_decimal(find_key_case_insensitive(entry, 'amount') or find_key_case_insensitive(entry, 'transAmt'))

            sft_type = find_key_case_insensitive(entry, 'sftType') or find_key_case_insensitive(entry, 'transactionType') or ''
            date_val = parse_date(find_key_case_insensitive(entry, 'date') or find_key_case_insensitive(entry, 'transDate'))

            if duplicate_action == 'merge':
                if IncomeTaxSft.objects.filter(user=user, financial_year=financial_year, transaction_type=sft_type, amount=amount, date=date_val).exists():
                    continue

            IncomeTaxSft.objects.create(
                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                transaction_type=sft_type, description=desc, amount=amount, date=date_val
            )
            counts['sft'] += 1

            if 'dividend' in desc.lower():
                company_name = find_key_case_insensitive(entry, 'companyName') or reporting_entity
                if duplicate_action == 'merge':
                    if IncomeTaxDividend.objects.filter(user=user, financial_year=financial_year, company_name=company_name, amount=amount).exists():
                        continue
                IncomeTaxDividend.objects.create(
                    user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                    company_name=company_name, amount=amount
                )
                counts['dividend'] += 1

            elif 'interest' in desc.lower() or 'fixed deposit' in desc.lower():
                bank_name = find_key_case_insensitive(entry, 'bankName') or reporting_entity
                int_type = 'Savings' if 'savings' in desc.lower() else 'Fixed Deposit'
                if duplicate_action == 'merge':
                    if IncomeTaxInterest.objects.filter(user=user, financial_year=financial_year, bank_name=bank_name, amount=amount).exists():
                        continue
                IncomeTaxInterest.objects.create(
                    user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                    bank_name=bank_name, interest_type=int_type, amount=amount
                )
                counts['interest'] += 1

            elif 'mutual fund' in desc.lower() or 'mutual' in desc.lower():
                amc_name = find_key_case_insensitive(entry, 'amcName') or find_key_case_insensitive(entry, 'fundName') or reporting_entity
                scheme_name = find_key_case_insensitive(entry, 'schemeName') or desc
                tx_type = 'BUY' if 'purchase' in desc.lower() or 'buy' in desc.lower() or 'subscription' in desc.lower() else 'SELL'
                buy_val = amount if tx_type == 'BUY' else Decimal('0')
                sell_val = amount if tx_type == 'SELL' else Decimal('0')
                units_val = parse_decimal(find_key_case_insensitive(entry, 'units'))
                if duplicate_action == 'merge':
                    if IncomeTaxMutualFund.objects.filter(user=user, financial_year=financial_year, amc=amc_name, scheme=scheme_name, amount=amount).exists():
                        continue
                IncomeTaxMutualFund.objects.create(
                    user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                    amc=amc_name, scheme=scheme_name, purchase=buy_val, redemption=sell_val, units=units_val, amount=amount
                )
                counts['mutual_fund'] += 1

            elif 'equity' in desc.lower() or 'share' in desc.lower() or 'securities' in desc.lower():
                broker_name = find_key_case_insensitive(entry, 'brokerName') or reporting_entity
                isin_val = find_key_case_insensitive(entry, 'isin') or ''
                tx_type = 'BUY' if 'purchase' in desc.lower() or 'buy' in desc.lower() else 'SELL'
                buy_val = amount if tx_type == 'BUY' else Decimal('0')
                sell_val = amount if tx_type == 'SELL' else Decimal('0')
                qty_val = parse_decimal(find_key_case_insensitive(entry, 'quantity') or find_key_case_insensitive(entry, 'qty'))
                if duplicate_action == 'merge':
                    if IncomeTaxEquity.objects.filter(user=user, financial_year=financial_year, broker=broker_name, isin=isin_val, buy_value=buy_val, sell_value=sell_val).exists():
                        continue
                IncomeTaxEquity.objects.create(
                    user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                    broker=broker_name, isin=isin_val, buy_value=buy_val, sell_value=sell_val, quantity=qty_val
                )
                counts['equity'] += 1

        # 3. Process Tax Payments
        for entry in tax_payments:
            tax_type = find_key_case_insensitive(entry, 'taxType') or find_key_case_insensitive(entry, 'paymentType') or 'Taxes Paid'
            bsr_code = find_key_case_insensitive(entry, 'bsr') or find_key_case_insensitive(entry, 'bsrCode') or ''
            challan_no = find_key_case_insensitive(entry, 'challanNo') or find_key_case_insensitive(entry, 'challanNumber') or ''
            date_str = find_key_case_insensitive(entry, 'paymentDate') or find_key_case_insensitive(entry, 'dateOfPayment') or ''
            date_of_payment = parse_date(date_str)
            amount = parse_decimal(find_key_case_insensitive(entry, 'amount') or find_key_case_insensitive(entry, 'transAmt'))

            if duplicate_action == 'merge':
                if IncomeTaxTaxPaid.objects.filter(user=user, financial_year=financial_year, challan_number=challan_no, amount=amount).exists():
                    continue

            IncomeTaxTaxPaid.objects.create(
                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                tax_type=tax_type, bsr_code=bsr_code, challan_number=challan_no, date=date_of_payment, amount=amount
            )
            counts['tax_payment'] += 1

        # 4. Process Refunds
        for entry in refunds:
            ay = find_key_case_insensitive(entry, 'assessmentYear') or find_key_case_insensitive(entry, 'ay') or ''
            refund_amount = parse_decimal(find_key_case_insensitive(entry, 'refundAmount') or find_key_case_insensitive(entry, 'amount'))
            interest = parse_decimal(find_key_case_insensitive(entry, 'interest') or '0')
            date_str = find_key_case_insensitive(entry, 'refundDate') or find_key_case_insensitive(entry, 'dateOfRefund') or ''
            date_of_refund = parse_date(date_str)
            refund_mode = find_key_case_insensitive(entry, 'refundMode') or ''

            if duplicate_action == 'merge':
                if IncomeTaxRefund.objects.filter(user=user, financial_year=financial_year, assessment_year=ay, refund_amount=refund_amount).exists():
                    continue

            IncomeTaxRefund.objects.create(
                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                assessment_year=ay, refund_amount=refund_amount, date=date_of_refund, status=refund_mode or 'Refund Paid'
            )
            counts['refund'] += 1

        # 5. Process Demands
        for entry in demands:
            ay = find_key_case_insensitive(entry, 'assessmentYear') or find_key_case_insensitive(entry, 'ay') or ''
            demand_amount = parse_decimal(find_key_case_insensitive(entry, 'demandAmount') or find_key_case_insensitive(entry, 'amount') or find_key_case_insensitive(entry, 'outstandingDemand'))
            section_code = find_key_case_insensitive(entry, 'section') or find_key_case_insensitive(entry, 'sectionCode') or ''

            if duplicate_action == 'merge':
                if IncomeTaxDemand.objects.filter(user=user, financial_year=financial_year, assessment_year=ay, outstanding_demand=demand_amount).exists():
                    continue

            IncomeTaxDemand.objects.create(
                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                assessment_year=ay, outstanding_demand=demand_amount, status=section_code or 'Outstanding'
            )
            counts['demand'] += 1

        # 6. Process Others
        for entry in others:
            category = find_key_case_insensitive(entry, 'category') or ''
            desc = find_key_case_insensitive(entry, 'description') or find_key_case_insensitive(entry, 'desc') or ''
            amount = parse_decimal(find_key_case_insensitive(entry, 'amount') or find_key_case_insensitive(entry, 'transAmt'))

            if duplicate_action == 'merge':
                if IncomeTaxOther.objects.filter(user=user, financial_year=financial_year, category=category, description=desc, amount=amount).exists():
                    continue

            IncomeTaxOther.objects.create(
                user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=entry,
                category=category, description=desc, amount=amount
            )
            counts['other'] += 1

    # Write aggregated salary records to database
    for emp_name, agg in salary_aggregates.items():
        if duplicate_action == 'merge':
            if IncomeTaxSalary.objects.filter(user=user, financial_year=financial_year, employer_name=emp_name, salary=agg['salary']).exists():
                continue
        IncomeTaxSalary.objects.create(
            user=user, financial_year=financial_year, source=source, imported_on=imported_on, json_reference=agg['json_reference'],
            employer_name=emp_name, salary=agg['salary'], perquisites=agg['perquisites'], tax_deducted=agg['tax_deducted']
        )
        counts['salary'] += 1

    update_user_tax_profile(user, financial_year, counts)

    return counts, None


def extract_part_a_profile(data):
    """
    Extracts Part A profile details.
    """
    part_a = find_key_case_insensitive(data, 'partA') or find_key_case_insensitive(data, 'personalInfo') or data
    if not isinstance(part_a, dict):
        part_a = data
        
    profile = {
        'pan': '',
        'aadhaar': '',
        'name': '',
        'dob': '',
        'email': '',
        'mobile': '',
        'address': ''
    }
    
    # 1. Try columnLabel and columnData mapping first (official AIS format)
    column_label = find_key_case_insensitive(part_a, 'columnLabel')
    column_data = find_key_case_insensitive(part_a, 'columnData')
    if isinstance(column_label, list) and isinstance(column_data, list):
        for label, val in zip(column_label, column_data):
            label_lower = str(label).lower()
            val_str = str(val).strip()
            if 'pan' in label_lower or 'permanent account' in label_lower:
                profile['pan'] = val_str
            elif 'aadhaar' in label_lower or 'aadhar' in label_lower or 'uid' in label_lower:
                profile['aadhaar'] = val_str
            elif 'name' in label_lower or 'assessee' in label_lower:
                profile['name'] = val_str
            elif 'dob' in label_lower or 'birth' in label_lower or 'incorporation' in label_lower:
                profile['dob'] = val_str
            elif 'email' in label_lower or 'mail' in label_lower:
                profile['email'] = val_str
            elif 'mobile' in label_lower or 'phone' in label_lower:
                profile['mobile'] = val_str
            elif 'address' in label_lower:
                profile['address'] = val_str

    # 2. Try direct key lookups if some keys are still empty
    if not profile['pan']:
        profile['pan'] = str(find_key_case_insensitive(part_a, 'pan') or '').strip()
    if not profile['aadhaar']:
        profile['aadhaar'] = str(find_key_case_insensitive(part_a, 'aadhaar') or find_key_case_insensitive(part_a, 'aadhar') or find_key_case_insensitive(part_a, 'uid') or '').strip()
    if not profile['name']:
        profile['name'] = str(find_key_case_insensitive(part_a, 'name') or find_key_case_insensitive(part_a, 'taxpayerName') or '').strip()
    if not profile['dob']:
        profile['dob'] = str(find_key_case_insensitive(part_a, 'dob') or find_key_case_insensitive(part_a, 'dateOfBirth') or find_key_case_insensitive(part_a, 'dobIncorporation') or '').strip()
    if not profile['email']:
        profile['email'] = str(find_key_case_insensitive(part_a, 'email') or find_key_case_insensitive(part_a, 'emailId') or '').strip()
    if not profile['mobile']:
        profile['mobile'] = str(find_key_case_insensitive(part_a, 'mobile') or find_key_case_insensitive(part_a, 'mobileNo') or find_key_case_insensitive(part_a, 'phone') or '').strip()
    if not profile['address']:
        addr_val = find_key_case_insensitive(part_a, 'address') or ''
        if isinstance(addr_val, dict):
            addr_parts = [str(v) for v in addr_val.values() if v]
            profile['address'] = ", ".join(addr_parts)
        else:
            profile['address'] = str(addr_val).strip()

    # 3. Fallback to metadata for PAN if still empty
    if not profile['pan']:
        metadata = find_key_case_insensitive(data, 'metadata')
        if isinstance(metadata, dict):
            profile['pan'] = str(find_key_case_insensitive(metadata, 'loggedInPan') or '').strip()

    return profile


def update_user_tax_profile(user, financial_year, counts):
    """
    Summarizes key aggregates from imported tables and updates/pre-fills the UserTaxProfile.
    """
    from .models import UserTaxProfile
    
    fy_norm = financial_year
    if len(financial_year) == 7: # e.g. 2025-26
        parts = financial_year.split('-')
        fy_norm = f"{parts[0]}-20{parts[1]}"

    # Calculate Aggregates
    salary_total = Decimal('0')
    for sal in IncomeTaxSalary.objects.filter(user=user, financial_year=financial_year):
        salary_total += sal.salary

    other_income = Decimal('0')
    for interest in IncomeTaxInterest.objects.filter(user=user, financial_year=financial_year):
        other_income += interest.amount
    for div in IncomeTaxDividend.objects.filter(user=user, financial_year=financial_year):
        other_income += div.amount

    profile, created = UserTaxProfile.objects.get_or_create(
        user=user,
        financial_year=fy_norm,
        defaults={
            'salary': salary_total,
            'other_taxable_income': other_income,
        }
    )
    if not created:
        profile.salary = salary_total
        profile.other_taxable_income = other_income
        profile.save()
