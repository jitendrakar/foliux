import requests
import logging
from decimal import Decimal
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_URL = "https://api.mfapi.in/mf"

def search_mf_schemes(query):
    """Search for mutual fund schemes by name or code."""
    if not query:
        return []
    url = f"{BASE_URL}/search?q={query}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error searching MF schemes for '{query}': {e}")
        return []

def get_mf_details(scheme_code):
    """Fetch details and full NAV history for a specific scheme."""
    if not scheme_code:
        return None
    url = f"{BASE_URL}/{scheme_code}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching MF details for {scheme_code}: {e}")
        return None

def get_latest_nav(scheme_code):
    """Fetch only the latest NAV for a scheme."""
    # The API doesn't have a specific 'latest' endpoint that is faster, 
    # but we can get it from the main detail response.
    data = get_mf_details(scheme_code)
    if data and data.get('data'):
        latest = data['data'][0]
        return {
            'nav': Decimal(str(latest['nav'])),
            'date': latest['date'],
            'meta': data.get('meta', {})
        }
    return None

def sync_fund_from_mfapi(fund):
    """Update a MutualFund model instance using data from mfapi.in."""
    from core.models import MutualFund
    
    scheme_code = getattr(fund, 'scheme_code', None)
    if not scheme_code:
        # Try to find scheme_code by searching for name if missing?
        # For now, we assume scheme_code is set.
        return False
        
    details = get_mf_details(scheme_code)
    if not details or not details.get('data'):
        return False
        
    latest_nav_data = details['data'][0]
    nav = Decimal(str(latest_nav_data['nav']))
    
    fund.prev_nav = fund.nav
    fund.nav = nav
    fund.last_updated = timezone.now()
    
    # Update meta if available
    meta = details.get('meta', {})
    if meta:
        fund.name = meta.get('scheme_name', fund.name)
        fund.amc = meta.get('fund_house', fund.amc)
        # ISIN if available in meta? The API meta usually includes scheme_category, etc.
        # ISIN is not always in meta.
        
    fund.save()
    return True
