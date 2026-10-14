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
    clean = re.sub(r'\(.*?\)', '', clean)
    clean = re.sub(r'IPO.*$', '', clean, flags=re.I).strip()
    clean = re.sub(r'(NSE|BSE)\s*(SME)?.*$', '', clean, flags=re.I).strip()
    clean = clean.replace(" Limited", "").replace(" Ltd.", "").strip()
    return clean


def parse_decimal(val: Any) -> Optional[Decimal]:
    """Parses a Decimal value from strings like '33', '11.42%', '₹289.00', '13.99x'."""
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


def scrape_investorgain_gmp_detail(url_or_slug: str) -> Optional[Dict[str, Any]]:
    """
    Scrapes individual Investorgain IPO GMP review page (e.g. https://www.investorgain.com/gmp/fusion-cx-ipo-gmp/1792/).
    Extracts latest live GMP amount, GMP percentage, upper price, estimated listing price, and subscription multiplier.
    """
    if not url_or_slug:
        return None

    if url_or_slug.startswith('http'):
        url = url_or_slug
    elif url_or_slug.startswith('/'):
        url = f"https://www.investorgain.com{url_or_slug}"
    else:
        url = f"https://www.investorgain.com/gmp/{url_or_slug}/"

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')

            data = {
                'url': url,
                'name': '',
                'gmp_amount': None,
                'gmp_percent': None,
                'price': None,
                'est_listing_price': None,
                'subscription_times': None,
                'trend': '',
            }

            # Extract name from H1 or Title
            h1 = soup.find('h1')
            if h1:
                raw_h1 = h1.get_text(strip=True)
                clean = re.sub(r'\s+IPO\s+GMP.*$', '', raw_h1, flags=re.I).strip()
                data['name'] = clean_investorgain_name(clean)

            # Table 0: GMP history & latest stats
            t0 = soup.find('table')
            if t0:
                header_text = t0.get_text()
                m_price = re.search(r'upper price[^\d]*(\d+(?:\.\d+)?)', header_text, re.I)
                if m_price:
                    data['price'] = parse_decimal(m_price.group(1))

                rows = t0.find_all('tr')
                if len(rows) > 1:
                    first_data_row = rows[1]
                    tds = [td.get_text(strip=True) for td in first_data_row.find_all(['th', 'td'])]
                    if len(tds) >= 2:
                        # Date / Sub column (e.g. '14-Oct 15:02Sub: 0.32xO')
                        m_sub = re.search(r'Sub:\s*(\d+(?:\.\d+)?)\s*x', tds[0], re.I)
                        if m_sub:
                            data['subscription_times'] = parse_decimal(m_sub.group(1))

                        # GMP column (e.g. '₹33(11.42%)' or '₹91(33.58%)')
                        m_gmp = re.search(r'([+-]?\d+(?:\.\d+)?)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*%\s*\)', tds[1])
                        if m_gmp:
                            data['gmp_amount'] = parse_decimal(m_gmp.group(1))
                            data['gmp_percent'] = parse_decimal(m_gmp.group(2))
                        else:
                            m_amt = parse_decimal(tds[1])
                            if m_amt is not None:
                                data['gmp_amount'] = m_amt

                        if len(tds) >= 3:
                            data['est_listing_price'] = parse_decimal(tds[2])
                        if len(tds) >= 5:
                            data['trend'] = tds[4]

            # Fallback for subscription if not in row 1
            if data['subscription_times'] is None:
                sub_match = re.search(r'Subscription[^\d]*(\d+(?:\.\d+)?)\s*x', soup.get_text(), re.I)
                if sub_match:
                    data['subscription_times'] = parse_decimal(sub_match.group(1))

            return data

    except Exception as e:
        logger.warning(f"Error scraping Investorgain GMP detail from '{url}': {e}")
        return None


def fetch_investorgain_gmp() -> Dict[str, Dict[str, Any]]:
    """
    Scrapes live IPO Grey Market Premium (GMP) data from Investorgain (https://www.investorgain.com/report/ipo-gmp-live/331/).
    Returns a dictionary keyed by clean lower-case IPO name, simple alphanumeric name, and slug containing:
    - name (clean company name)
    - raw_name
    - gmp_amount (Decimal)
    - gmp_percent (Decimal)
    - price (Decimal)
    - subscription_times (Decimal)
    - url (individual review page URL)
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

                # Extract individual review page URL from <a> tag
                a_tag = row.find('a', href=True)
                detail_url = ""
                slug = ""
                if a_tag and a_tag.get('href'):
                    href = a_tag['href']
                    detail_url = href if href.startswith('http') else f"https://www.investorgain.com{href}"
                    m_slug = re.search(r'/gmp/([^/]+)/', href)
                    if m_slug:
                        slug = m_slug.group(1)

                gmp_cell = tds[1]
                # Match GMP format: '40(13.84%)' or '1.5(1.83%)' or '67(24.72%)' or '₹91(33.58%)'
                m = re.search(r'([+-]?\d+(?:\.\d+)?)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*%\s*\)', gmp_cell)
                gmp_amt = parse_decimal(m.group(1)) if m else None
                gmp_pct = parse_decimal(m.group(2)) if m else None

                # Extract price & subscription if present in table
                sub_val = parse_decimal(tds[3]) if len(tds) > 3 else None
                price_val = parse_decimal(tds[4]) if len(tds) > 4 else None

                record = {
                    'name': c_name,
                    'raw_name': raw_name,
                    'gmp_amount': gmp_amt,
                    'gmp_percent': gmp_pct,
                    'price': price_val,
                    'subscription_times': sub_val,
                    'url': detail_url,
                    'slug': slug,
                }

                # Primary key
                gmp_records[c_name.lower()] = record

                # Key without special chars
                simple_key = re.sub(r'[^a-z0-9]', '', c_name.lower())
                if simple_key:
                    gmp_records[simple_key] = record

                # URL Slug keys (e.g. 'fusion-cx-ipo', 'fusion-cx', 'hd-fire-protect')
                if slug:
                    gmp_records[slug.lower()] = record
                    clean_slug = re.sub(r'-ipo$', '', slug.lower())
                    clean_slug = re.sub(r'-sme$', '', clean_slug)
                    clean_slug_space = clean_slug.replace('-', ' ')
                    gmp_records[clean_slug] = record
                    gmp_records[clean_slug_space] = record
                    simple_slug = re.sub(r'[^a-z0-9]', '', clean_slug)
                    if simple_slug:
                        gmp_records[simple_slug] = record

    except Exception as e:
        logger.error(f"Error scraping Investorgain GMP: {e}")

    return gmp_records


def match_investorgain_record(ipo_name: str, ig_records: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Finds the best matching Investorgain record for a given IPO name using:
    1. Exact normalized lowercase match
    2. Alphanumeric match (ignoring spaces & punctuation)
    3. Cleaned substring match (e.g. 'Zetwerk' in 'Zetwerk Manufacturing Business')
    """
    if not ipo_name or not ig_records:
        return None

    c_name = clean_investorgain_name(ipo_name).lower()
    s_name = re.sub(r'[^a-z0-9]', '', c_name)

    # 1. Exact match
    if c_name in ig_records:
        return ig_records[c_name]

    # 2. Alphanumeric match
    if s_name in ig_records:
        return ig_records[s_name]

    # 3. Substring match against distinct records
    seen_urls = set()
    for rec in ig_records.values():
        rec_url = rec.get('url', '')
        if rec_url in seen_urls:
            continue
        seen_urls.add(rec_url)

        rec_name = clean_investorgain_name(rec.get('name', '')).lower()
        if not rec_name or len(rec_name) < 4:
            continue

        if rec_name == c_name or rec_name in c_name or c_name in rec_name:
            return rec

        # Check slug
        slug = rec.get('slug', '').lower()
        if slug:
            clean_slug = re.sub(r'-ipo$', '', slug).replace('-', ' ')
            if clean_slug and len(clean_slug) >= 4 and (clean_slug in c_name or c_name in clean_slug):
                return rec

    return None
