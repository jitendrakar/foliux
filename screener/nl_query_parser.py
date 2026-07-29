import re
from typing import Dict, Any, List, Tuple

def parse_natural_language_query(query_text: str) -> Dict[str, Any]:
    """
    Parses plain English stock screening queries into structured parameters,
    conditions, filter tags, and ordering rules.
    """
    text = query_text.lower().strip()
    text = re.sub(r'[\?\!\,\;]', ' ', text)
    
    filters = {}
    tags = []
    sort_by = '-foliux_score'

    # --- 1. PE RATIO ---
    pe_between = re.search(r'(?:pe|p/e|price to earnings)\s*(?:ratio)?\s*(?:between)?\s*(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*(\d+(?:\.\d+)?)', text)
    if pe_between:
        low, high = float(pe_between.group(1)), float(pe_between.group(2))
        filters['pe_ratio__gte'] = low
        filters['pe_ratio__lte'] = high
        tags.append({'label': f"PE Ratio: {low} - {high}", 'metric': 'pe_ratio'})
    else:
        pe_match = re.search(r'(?:pe|p/e|price to earnings)\s*(?:ratio)?\s*(?:below|under|less than|<=|<)\s*(\d+(?:\.\d+)?)', text)
        if pe_match:
            val = float(pe_match.group(1))
            filters['pe_ratio__lte'] = val
            tags.append({'label': f"PE Ratio < {val}", 'metric': 'pe_ratio'})
        else:
            pe_above = re.search(r'(?:pe|p/e|price to earnings)\s*(?:ratio)?\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)', text)
            if pe_above:
                val = float(pe_above.group(1))
                filters['pe_ratio__gte'] = val
                tags.append({'label': f"PE Ratio > {val}", 'metric': 'pe_ratio'})

    # --- 2. ROE ---
    roe_match = re.search(r'(?:roe|return on equity)\s*(?:above|over|greater than|above|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if roe_match:
        val = float(roe_match.group(1))
        filters['roe__gte'] = val
        tags.append({'label': f"ROE > {val}%", 'metric': 'roe'})
    else:
        roe_below = re.search(r'(?:roe|return on equity)\s*(?:below|under|less than|<=|<)\s*(\d+(?:\.\d+)?)\%?', text)
        if roe_below:
            val = float(roe_below.group(1))
            filters['roe__lte'] = val
            tags.append({'label': f"ROE < {val}%", 'metric': 'roe'})

    # --- 3. ROCE ---
    roce_match = re.search(r'(?:roce|return on capital employed)\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if roce_match:
        val = float(roce_match.group(1))
        filters['roce__gte'] = val
        tags.append({'label': f"ROCE > {val}%", 'metric': 'roce'})

    # --- 4. DEBT TO EQUITY & LOW DEBT ---
    de_match = re.search(r'(?:debt to equity|debt/equity|d/e)\s*(?:below|under|less than|<=|<)\s*(\d+(?:\.\d+)?)', text)
    if de_match:
        val = float(de_match.group(1))
        filters['debt_to_equity__lte'] = val
        tags.append({'label': f"Debt to Equity < {val}", 'metric': 'debt_to_equity'})
    elif 'low debt' in text or 'zero debt' in text or 'debt free' in text:
        filters['debt_to_equity__lte'] = 0.5
        tags.append({'label': "Low Debt (D/E < 0.5)", 'metric': 'debt_to_equity'})

    # --- 5. MARKET CAP & SMALL CAP ---
    mcap_match = re.search(r'(?:market cap|mcap|market capitalization)\s*(?:above|over|greater than|>=|>)\s*₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:cr|crore)?', text)
    if mcap_match:
        val = float(mcap_match.group(1).replace(',', ''))
        filters['market_cap__gte'] = val
        tags.append({'label': f"Market Cap > ₹{val:,.0f} Cr.", 'metric': 'market_cap'})
    elif 'small cap' in text or 'smallcap' in text:
        filters['market_cap__lte'] = 10000
        tags.append({'label': "Small Cap (Market Cap < ₹10,000 Cr.)", 'metric': 'market_cap'})
    elif 'large cap' in text or 'largecap' in text:
        filters['market_cap__gte'] = 50000
        tags.append({'label': "Large Cap (Market Cap > ₹50,000 Cr.)", 'metric': 'market_cap'})

    # --- 6. SALES & PROFIT GROWTH ---
    sales_match = re.search(r'(?:sales growth|revenue growth)\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if sales_match:
        val = float(sales_match.group(1))
        filters['sales_growth__gte'] = val
        tags.append({'label': f"Sales Growth > {val}%", 'metric': 'sales_growth'})

    profit_match = re.search(r'(?:profit growth|net profit growth)\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if profit_match:
        val = float(profit_match.group(1))
        filters['profit_growth__gte'] = val
        tags.append({'label': f"Profit Growth > {val}%", 'metric': 'profit_growth'})

    # --- 7. DIVIDEND YIELD ---
    div_match = re.search(r'(?:dividend yield|dividend)\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if div_match:
        val = float(div_match.group(1))
        filters['dividend_yield__gte'] = val
        tags.append({'label': f"Dividend Yield > {val}%", 'metric': 'dividend_yield'})

    # --- 8. PROMOTER HOLDING ---
    prom_match = re.search(r'(?:promoter holding|promoter)\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if prom_match:
        val = float(prom_match.group(1))
        filters['promoter_holding__gte'] = val
        tags.append({'label': f"Promoter Holding > {val}%", 'metric': 'promoter_holding'})

    # --- 9. 52-WEEK HIGH / TECHNICAL ---
    if '52-week high' in text or '52 week high' in text or 'new highs' in text:
        filters['at_52w_high'] = True
        tags.append({'label': "Near 52-Week High", 'metric': '52w_high'})

    # --- 10. MANAGEMENT RELIABILITY SCORE & FORECASTS ---
    rel_score_match = re.search(r'(?:management reliability|reliability score|management score|credibility score|credibility)\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if rel_score_match:
        val = int(float(rel_score_match.group(1)))
        filters['reliability_score__gte'] = val
        tags.append({'label': f"Management Reliability Score > {val}%", 'metric': 'reliability_score'})

    fc_achieve_match = re.search(r'(?:forecast achievement|forecasts achieved|guidance achieved|achievement)\s*(?:above|over|greater than|>=|>)\s*(\d+(?:\.\d+)?)\%?', text)
    if fc_achieve_match:
        val = float(fc_achieve_match.group(1))
        filters['forecast_achievement_pct__gte'] = val
        tags.append({'label': f"Forecast Achievement > {val}%", 'metric': 'forecast_achievement'})

    fc_count_match = re.search(r'(?:more than|above|>)\s*(\d+)\s*(?:management forecasts|guidance items|forecasts)', text)
    if fc_count_match:
        val = int(fc_count_match.group(1))
        filters['total_forecasts__gte'] = val
        tags.append({'label': f"Total Forecasts > {val}", 'metric': 'forecast_count'})

    if 'no delayed projects' in text or 'zero delay' in text or 'delivered all' in text:
        filters['delayed_count'] = 0
        tags.append({'label': "Zero Project Delays", 'metric': 'no_delays'})

    if 'highest management credibility' in text or 'highest reliability' in text or 'best management' in text:
        sort_by = '-reliability_score__overall_score'
        tags.append({'label': "Highest Management Credibility Ranking", 'metric': 'ranking'})

    return {
        'raw_query': query_text,
        'filters': filters,
        'tags': tags,
        'sort_by': sort_by
    }
