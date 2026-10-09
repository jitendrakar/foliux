import re
import logging
import urllib.request
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

INVESTORGAIN_GMP_URL = "https://www.investorgain.com/report/ipo-gmp-live/331/"

def clean_investorgain_name(raw_name: str) -> str:
    """Cleans raw IPO name from Investorgain table."""
    if not raw_name:
        return ""
    clean = raw_name.strip()
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'IPO.*$', '', clean, flags=re.I).strip()
    clean = re.sub(r'(NSE|BSE)\s*(SME)?.*$', '', clean, flags=re.I).strip()
    clean = clean.replace(" Limited", "").replace(" Ltd.", "").strip()
    return clean

def parse_decimal(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    s = str(val).strip().replace(',', '')
    m = re.search(r'([+-]?\d+(?:\.\d+)?)', s)
    if m:
        try:
            return Decimal(m.group(1))
        except Exception:
            pass
    return None

def fetch_investorgain_gmp() -> Dict[str, Dict[str, Any]]:
    """
    Scrapes live IPO Grey Market Premium (GMP) data from Investorgain (https://www.investorgain.com/report/ipo-gmp-live/331/).
    Returns a dictionary keyed by clean lower-case IPO name containing:
    - clean_name
    - gmp_amount (Decimal)
    - gmp_percent (Decimal)
    - price (Decimal)
    - subscription_times (Decimal)
    """
    gmp_records = {}
    try:
        req = urllib.request.Request(INVESTORGAIN_GMP_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            tables = soup.find_all('table')
            if not tables:
                logger.warning("No tables found on Investorgain GMP page")
                return {}

            main_table = tables[0]
            rows = main_table.find_all('tr')
            for row in rows:
                tds = [td.get_text(strip=True) for td in row.find_all(['th', 'td'])]
                if len(tds) < 2:
                    continue

                raw_name = tds[0]
                if not raw_name or 'Name' in raw_name or 'Company' in raw_name:
                    continue

                c_name = clean_investorgain_name(raw_name)
                if not c_name:
                    continue

                gmp_cell = tds[1]
                # Match GMP format: '40(13.84%)' or '1.5(1.83%)' or '67(24.72%)'
                m = re.search(r'([+-]?\d+(?:\.\d+)?)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*%\s*\)', gmp_cell)
                
                gmp_amt = parse_decimal(m.group(1)) if m else None
                gmp_pct = parse_decimal(m.group(2)) if m else None

                # Extract price & subscription if present in table
                price_val = parse_decimal(tds[4]) if len(tds) > 4 else None
                sub_val = parse_decimal(tds[3]) if len(tds) > 3 else None

                record = {
                    'name': c_name,
                    'raw_name': raw_name,
                    'gmp_amount': gmp_amt,
                    'gmp_percent': gmp_pct,
                    'price': price_val,
                    'subscription_times': sub_val,
                }
                gmp_records[c_name.lower()] = record
                # Also store key without special chars for fuzzy matching
                simple_key = re.sub(r'[^a-z0-9]', '', c_name.lower())
                if simple_key:
                    gmp_records[simple_key] = record

    except Exception as e:
        logger.error(f"Error scraping Investorgain GMP: {e}")

    return gmp_records
