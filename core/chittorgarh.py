import re
import logging
import urllib.request
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def parse_chittorgarh_dates(date_str: str, default_year: Optional[int] = None) -> Tuple[Optional[date], Optional[date]]:
    """
    Parses start_date and end_date from Chittorgarh date string formats:
    - '11 to 16 Sep, 2026'
    - '16 - 18 Sep'
    - 'Sep 11 to Sep 16, 2026'
    - 'Friday, September 11, 2026'
    - '11-Sep-2026'
    """
    if not date_str:
        return None, None
        
    date_str = date_str.strip()
    current_year = default_year or datetime.now().year

    # Pattern 1: DD to DD Month, YYYY or DD - DD Month YYYY or DD to DD Month
    m1 = re.search(r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s+([A-Za-z]+)(?:[,\s]+(\d{4}))?', date_str, re.I)
    if m1:
        d1, d2, month_str, yr = m1.groups()
        yr = int(yr) if yr else current_year
        try:
            dt1 = datetime.strptime(f"{d1} {month_str[:3]} {yr}", "%d %b %Y").date()
            dt2 = datetime.strptime(f"{d2} {month_str[:3]} {yr}", "%d %b %Y").date()
            return dt1, dt2
        except Exception:
            pass

    # Pattern 2: Month DD to Month DD, YYYY
    m2 = re.search(r'([A-Za-z]+)\s+(\d{1,2})\s*(?:to|-)\s*([A-Za-z]+)?\s*(\d{1,2})(?:[,\s]+(\d{4}))?', date_str, re.I)
    if m2:
        m_str1, d1, m_str2, d2, yr = m2.groups()
        m_str2 = m_str2 or m_str1
        yr = int(yr) if yr else current_year
        try:
            dt1 = datetime.strptime(f"{d1} {m_str1[:3]} {yr}", "%d %b %Y").date()
            dt2 = datetime.strptime(f"{d2} {m_str2[:3]} {yr}", "%d %b %Y").date()
            return dt1, dt2
        except Exception:
            pass

    # Pattern 3: Single date string
    clean_str = re.sub(r'^[A-Za-z]+,\s*', '', date_str)
    for fmt in ["%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%d-%b-%Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(clean_str, fmt).date()
            return dt, dt
        except ValueError:
            pass

    return None, None


def parse_decimal_value(val_str: Any) -> Optional[Decimal]:
    """Extracts a decimal number from a string (e.g. '3.50x', '35%', '₹15.50')."""
    if val_str is None:
        return None
    s = str(val_str).strip()
    m = re.search(r'([+-]?\d+(?:\.\d+)?)', s)
    if m:
        try:
            return Decimal(m.group(1))
        except Exception:
            pass
    return None


def fetch_url_soup(url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            return BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.warning(f"Error fetching URL '{url}': {e}")
        return None


import concurrent.futures

def fetch_chittorgarh_ipos() -> List[Dict[str, Any]]:
    """
    Primary Chittorgarh IPO Scraper.
    Checks Upcoming and Ongoing IPOs from Chittorgarh (https://www.chittorgarh.com/).
    Returns a list of dictionary records containing scraped IPO metadata.
    """
    dashboard_urls = [
        "https://www.chittorgarh.com/ipo/ipo_dashboard.asp",
        "https://www.chittorgarh.com/ipo/ipo_dashboard.asp?a=sme"
    ]
    
    tasks_to_scrape = []
    seen_urls = set()

    for d_url in dashboard_urls:
        soup = fetch_url_soup(d_url)
        if not soup:
            logger.warning(f"Failed to load Chittorgarh IPO dashboard: {d_url}")
            continue

        tables = soup.find_all('table')
        if not tables:
            continue

        main_table = tables[0]
        rows = main_table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if not cells:
                continue
                
            a_tag = row.find('a', href=True)
            if not a_tag:
                continue
                
            link_href = a_tag['href']
            raw_name = a_tag.get_text(strip=True)
            if not raw_name or 'Company' in raw_name:
                continue

            row_text = row.get_text(strip=True)
            ipo_url = link_href if link_href.startswith('http') else f"https://www.chittorgarh.com{link_href}"
            if ipo_url not in seen_urls:
                seen_urls.add(ipo_url)
                tasks_to_scrape.append((ipo_url, raw_name, row_text))

    scraped_ipos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(scrape_chittorgarh_ipo_detail, url, name, text)
            for url, name, text in tasks_to_scrape
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if res:
                    scraped_ipos.append(res)
            except Exception as e:
                logger.warning(f"Error in parallel Chittorgarh IPO scrape: {e}")

    return scraped_ipos


def scrape_chittorgarh_ipo_detail(url: str, default_name: str, row_text: str = "") -> Optional[Dict[str, Any]]:
    """Scrapes individual Chittorgarh IPO page for dates, company work, registrar, subscription, GMP, and detailed notes/analysis."""
    soup = fetch_url_soup(url)
    if not soup:
        return None

    name = default_name.strip()
    clean_name = re.sub(r'\s+IPO$', '', name, flags=re.I).strip()
    
    start_date = None
    end_date = None
    company_work = ""
    symbol = None
    registrar_name = ""
    registrar_slug = ""
    subscription_times = None
    gmp_percent = None
    gmp_amount = None

    # Check Key Table 0 on detail page
    tables = soup.find_all('table')
    if tables:
        t0 = tables[0]
        for tr in t0.find_all('tr'):
            tds = [td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]
            if len(tds) >= 2:
                key = tds[0].lower()
                val = tds[1]
                if 'ipo date' in key or 'issue date' in key:
                    start_date, end_date = parse_chittorgarh_dates(val)
                elif 'symbol' in key or 'ticker' in key:
                    symbol = val.strip()

    if not start_date and row_text:
        start_date, end_date = parse_chittorgarh_dates(row_text)

    # 1. Company Work & Business Description
    about_hdr = soup.find(string=re.compile(r'About the Company|Company Profile|Business Overview', re.I))
    about_text_list = []
    if about_hdr:
        curr = about_hdr.parent
        for _ in range(8):
            curr = curr.find_next(['p', 'ul', 'ol'])
            if not curr:
                break
            txt = curr.get_text(strip=True)
            if len(txt) > 30 and not any(k in txt for k in ['Copyright', 'Reach over', 'Login']):
                about_text_list.append(txt)
    
    if about_text_list:
        company_work = about_text_list[0]
    else:
        company_work = f"{clean_name} Initial Public Offering."

    # 2. Objects of the Issue
    obj_hdr = soup.find(string=re.compile(r'Objects of the Issue|Use of Proceeds', re.I))
    obj_text_list = []
    if obj_hdr:
        curr = obj_hdr.parent
        for _ in range(6):
            curr = curr.find_next(['p', 'ul', 'ol'])
            if not curr:
                break
            txt = curr.get_text(strip=True)
            if len(txt) > 20 and not any(k in txt for k in ['Copyright', 'Reach over']):
                obj_text_list.append(txt)

    # 3. IPO Summary & Issue Details Paragraphs
    issue_paragraphs = []
    for p in soup.find_all('p'):
        txt = p.get_text(strip=True)
        if any(k in txt.lower() for k in ['book build issue', 'fresh issue', 'price band', 'opens for subscription', 'allotment for', 'lead manager']):
            issue_paragraphs.append(txt)

    # Extract Key Performance Indicators (KPI) and IPO Valuation tables
    kpi_data, val_data = extract_chittorgarh_kpi_and_valuation(soup)
    kpi_val_notes = format_kpi_and_valuation_notes(kpi_data, val_data)

    # Construct Rich Detailed Analysis & Notes
    notes_parts = []
    if issue_paragraphs:
        notes_parts.append("■ IPO SUMMARY & ISSUE DETAILS:\n" + "\n".join(issue_paragraphs[:4]))
    if about_text_list:
        notes_parts.append("■ COMPANY PROFILE & BUSINESS OVERVIEW:\n" + "\n".join(about_text_list[:4]))
    if obj_text_list:
        notes_parts.append("■ OBJECTS OF THE ISSUE:\n" + "\n".join(obj_text_list[:3]))
    if kpi_val_notes:
        notes_parts.append(kpi_val_notes)

    notes_parts.append(f"■ SOURCE & ATTRIBUTION:\nChittorgarh ({url})")
    full_notes = "\n\n".join(notes_parts)

    # Registrar Identification
    reg_link = soup.find('a', href=re.compile(r'ipo-registrar|registrar', re.I))
    if reg_link:
        registrar_name = reg_link.get_text(strip=True)
        reg_text_lower = registrar_name.lower()
        if 'kfin' in reg_text_lower:
            registrar_slug = 'kfintech'
        elif 'mufg' in reg_text_lower or 'link intime' in reg_text_lower or 'linkintime' in reg_text_lower:
            registrar_slug = 'mufg'
        elif 'bigshare' in reg_text_lower:
            registrar_slug = 'bigshare'

    # GMP in page text if present
    gmp_match = re.search(r'GMP\s*:?\s*₹?\s*(\d+(?:\.\d+)?)\s*(?:\((\d+(?:\.\d+)?)\s*%\))?', soup.get_text(), re.I)
    if gmp_match:
        gmp_amt_str, gmp_pct_str = gmp_match.groups()
        if gmp_amt_str:
            gmp_amount = parse_decimal_value(gmp_amt_str)
        if gmp_pct_str:
            gmp_percent = parse_decimal_value(gmp_pct_str)

    # Live IPO Subscription from Chittorgarh subscription page
    sub_url = None
    sub_link = soup.find('a', href=re.compile(r'/ipo_subscription/', re.I))
    if sub_link and sub_link.get('href'):
        href = sub_link['href']
        sub_url = href if href.startswith('http') else f"https://www.chittorgarh.com{href}"
    elif '/ipo/' in url:
        sub_url = re.sub(r'/ipo/', '/ipo_subscription/', url)

    if sub_url:
        try:
            subscription_times = scrape_chittorgarh_subscription(sub_url)
        except Exception as e:
            logger.warning(f"Error scraping subscription from {sub_url}: {e}")

    return {
        'name': clean_name,
        'symbol': symbol or "",
        'start_date': start_date,
        'end_date': end_date,
        'company_work': company_work,
        'notes': full_notes,
        'registrar_slug': registrar_slug or 'mufg',
        'registrar_name': registrar_name,
        'subscription_times': subscription_times,
        'gmp_percent': gmp_percent,
        'gmp_amount': gmp_amount,
        'kpi_data': kpi_data,
        'valuation_data': val_data,
        'url': url,
    }


def extract_chittorgarh_kpi_and_valuation(soup: BeautifulSoup) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extracts Key Performance Indicators (KPI) and IPO Valuation tables from a Chittorgarh IPO page.
    Returns:
        (kpi_dict, valuation_dict)
    """
    kpi_data = {}
    val_data = {}

    for table in soup.find_all('table'):
        t_text = table.get_text()
        rows = table.find_all('tr')
        if not rows:
            continue

        header_cells = [td.get_text(strip=True) for td in rows[0].find_all(['th', 'td'])]
        first_hdr = header_cells[0].lower() if header_cells else ''

        # 1. Key Performance Indicator (KPI) Table
        is_kpi_header = ('kpi' in first_hdr or 'key performance' in first_hdr)
        has_kpi_metrics = any(k in t_text for k in ['RoNW', 'PAT Margin', 'EBITDA Margin', 'NAV', 'P/B', 'ROE', 'ROCE'])
        if (is_kpi_header or has_kpi_metrics) and any(k in t_text for k in ['PAT Margin', 'EBITDA Margin', 'RoNW']):
            headers = [re.sub(r'\s+', ' ', c).strip() for c in header_cells]
            table_rows = []
            for tr in rows[1:]:
                cells = [re.sub(r'\s+', ' ', td.get_text(strip=True)).strip() for td in tr.find_all(['th', 'td'])]
                if cells and len(cells) >= 2:
                    table_rows.append(cells)
            if table_rows:
                kpi_data = {'headers': headers, 'rows': table_rows}

        # 2. IPO Valuation Table
        is_val_header = ('valuation' in first_hdr or 'valuation metric' in first_hdr or 'metric' in first_hdr)
        has_val_metrics = any(k in t_text for k in ['Pre IPO', 'Post IPO']) and any(k in t_text for k in ['EPS', 'P/E', 'Market Cap'])
        if (is_val_header or has_val_metrics) and any(k in t_text for k in ['EPS', 'P/E', 'Market Cap']):
            headers = [re.sub(r'\s+', ' ', c).strip() for c in header_cells]
            table_rows = []
            for tr in rows[1:]:
                cells = [re.sub(r'\s+', ' ', td.get_text(strip=True)).strip() for td in tr.find_all(['th', 'td'])]
                if cells:
                    cells[0] = re.sub(r'Cap\s*at', 'Cap at', cells[0])
                    cells[0] = re.sub(r'EPS\s*[\(\?₹Rs\.\)]+', 'EPS (₹)', cells[0])
                    cells = [re.sub(r'[\?]\s*(\d)', r'₹\1', c) for c in cells]
                if cells and len(cells) >= 2:
                    table_rows.append(cells)
            if table_rows:
                val_data = {'headers': headers, 'rows': table_rows}

    return kpi_data, val_data


def format_kpi_and_valuation_notes(kpi_data: Dict[str, Any], val_data: Dict[str, Any]) -> str:
    """Formats KPI and Valuation tables into human-readable text blocks for notes."""
    parts = []
    if kpi_data and kpi_data.get('rows'):
        headers = kpi_data.get('headers', [])
        period_str = " | ".join(headers[1:]) if len(headers) > 1 else ""
        lines = ["■ KEY PERFORMANCE INDICATORS (KPI):"]
        if period_str:
            lines.append(f"Period: {period_str}")
        for r in kpi_data['rows']:
            if len(r) >= 2:
                metric = r[0]
                vals = " | ".join(r[1:])
                lines.append(f"• {metric}: {vals}")
        parts.append("\n".join(lines))

    if val_data and val_data.get('rows'):
        headers = val_data.get('headers', [])
        sub_str = " | ".join(headers[1:]) if len(headers) > 1 else ""
        lines = ["■ IPO VALUATION:"]
        if sub_str:
            lines.append(f"Valuation: {sub_str}")
        for r in val_data['rows']:
            if len(r) >= 2:
                metric = r[0]
                vals = " | ".join(r[1:])
                lines.append(f"• {metric}: {vals}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def scrape_chittorgarh_subscription(sub_url: str) -> Optional[Decimal]:
    """Scrapes total subscription multiplier from Chittorgarh subscription page."""
    soup = fetch_url_soup(sub_url)
    if not soup:
        return None

    # Search through tables containing 'subscription'
    for table in soup.find_all('table'):
        t_text = table.get_text()
        if 'subscription' not in t_text.lower():
            continue

        for tr in table.find_all('tr'):
            tds = [td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]
            if len(tds) < 2:
                continue

            cat_name = tds[0].strip().lower()

            # Exact or prefix match for 'Total Subscription'
            if 'total subscription' in cat_name:
                for cell in tds[1:]:
                    val = parse_decimal_value(cell)
                    if val is not None:
                        return val

            # Or 'Total' within a table specifically tracking 'Subscription (times)'
            elif cat_name == 'total' and ('times' in t_text.lower() or any('times' in c.lower() for c in tds)):
                for cell in tds[1:]:
                    m = re.search(r'(\d+(?:\.\d+)?)\s*x', cell, re.I)
                    if m:
                        return Decimal(m.group(1))
                    val = parse_decimal_value(cell)
                    if val is not None and val < 10000:
                        return val

    # Fallback: search regex directly in the text of the page
    m_sub = re.search(r'Total\s+Subscription\s*[:\-|]?\s*(\d+(?:\.\d+)?)\s*x?', soup.get_text(), re.I)
    if m_sub:
        return parse_decimal_value(m_sub.group(1))

    return None
