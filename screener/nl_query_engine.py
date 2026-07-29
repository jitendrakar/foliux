from typing import Dict, Any, List
from django.db.models import Q
from screener.models import Company, ManagementReliabilityScore
from screener.nl_query_parser import parse_natural_language_query

def execute_nl_query(query_text: str) -> Dict[str, Any]:
    """
    Executes a natural language stock screening query across Company & ManagementReliabilityScore models,
    applying all parsed criteria and returning enriched results.
    """
    parsed = parse_natural_language_query(query_text)
    filters = parsed['filters']
    
    # Base Queryset with pre-joined reliability scores
    companies_qs = Company.objects.select_related('reliability_score').all()

    # Pre-filter by standard Django fields
    if 'pe_ratio__lte' in filters:
        companies_qs = companies_qs.filter(pe_ratio__lte=filters['pe_ratio__lte'])
    if 'pe_ratio__gte' in filters:
        companies_qs = companies_qs.filter(pe_ratio__gte=filters['pe_ratio__gte'])
    if 'roe__gte' in filters:
        companies_qs = companies_qs.filter(roe__gte=filters['roe__gte'])
    if 'roe__lte' in filters:
        companies_qs = companies_qs.filter(roe__lte=filters['roe__lte'])
    if 'roce__gte' in filters:
        companies_qs = companies_qs.filter(roce__gte=filters['roce__gte'])
    if 'market_cap__gte' in filters:
        companies_qs = companies_qs.filter(market_cap__gte=filters['market_cap__gte'])
    if 'market_cap__lte' in filters:
        companies_qs = companies_qs.filter(market_cap__lte=filters['market_cap__lte'])
    if 'sales_growth__gte' in filters:
        companies_qs = companies_qs.filter(sales_growth__gte=filters['sales_growth__gte'])
    if 'profit_growth__gte' in filters:
        companies_qs = companies_qs.filter(profit_growth__gte=filters['profit_growth__gte'])
    if 'dividend_yield__gte' in filters:
        companies_qs = companies_qs.filter(dividend_yield__gte=filters['dividend_yield__gte'])
    if 'promoter_holding__gte' in filters:
        companies_qs = companies_qs.filter(promoter_holding__gte=filters['promoter_holding__gte'])
    if 'reliability_score__gte' in filters:
        companies_qs = companies_qs.filter(reliability_score__overall_score__gte=filters['reliability_score__gte'])

    # Format enriched output list and apply calculated field filters
    matched_results = []
    for c in companies_qs:
        rel = getattr(c, 'reliability_score', None)
        
        # Calculate Debt to Equity (debt / market_cap)
        d_e = round(float(c.debt) / float(c.market_cap), 2) if float(c.market_cap or 0) > 0 else 0.0
        
        # Calculate Forecast Achievement %
        total_fc = rel.total_forecasts if rel else 0
        achieved_fc = rel.achieved_count if rel else 0
        partially_fc = rel.partially_achieved_count if rel else 0
        delayed_fc = rel.delayed_count if rel else 0
        not_achieved_fc = rel.not_achieved_count if rel else 0
        
        fc_achievement_pct = round((achieved_fc / total_fc * 100), 1) if total_fc > 0 else (float(rel.reliability_score_percent) if rel else 85.0)
        reliability_score_val = rel.overall_score if rel else 80
        ai_rating_val = rel.ai_credibility_rating if rel else 'High'

        # Apply calculated field filters
        if 'debt_to_equity__lte' in filters and d_e > filters['debt_to_equity__lte']:
            continue
        if 'forecast_achievement_pct__gte' in filters and fc_achievement_pct < filters['forecast_achievement_pct__gte']:
            continue
        if 'total_forecasts__gte' in filters and total_fc < filters['total_forecasts__gte']:
            continue
        if 'delayed_count' in filters and delayed_fc > filters['delayed_count']:
            continue

        matched_results.append({
            'id': c.id,
            'name': c.name,
            'nse_symbol': c.nse_symbol,
            'bse_symbol': c.bse_symbol or '',
            'sector': c.sector or 'Technology',
            'industry': c.industry or 'IT Services & Consulting',
            'current_price': float(c.current_price),
            'market_cap': float(c.market_cap),
            'pe_ratio': float(c.pe_ratio) if c.pe_ratio else 0.0,
            'pb_ratio': float(c.pb_ratio) if c.pb_ratio else 0.0,
            'roe': float(c.roe),
            'roce': float(c.roce),
            'debt_to_equity': d_e,
            'sales_growth': float(c.sales_growth),
            'profit_growth': float(c.profit_growth),
            'dividend_yield': float(c.dividend_yield),
            'promoter_holding': float(c.promoter_holding),
            'reliability_score': reliability_score_val,
            'forecast_achievement_pct': fc_achievement_pct,
            'total_forecasts': total_fc,
            'achieved_count': achieved_fc,
            'partially_achieved_count': partially_fc,
            'delayed_count': delayed_fc,
            'not_achieved_count': not_achieved_fc,
            'ai_credibility_rating': ai_rating_val,
            'foliux_score': c.foliux_score or max(70, reliability_score_val),
            'high_52w': float(c.high_52w),
            'low_52w': float(c.low_52w),
        })

    # Sort results
    if parsed['sort_by'] == '-reliability_score__overall_score':
        matched_results.sort(key=lambda x: x['reliability_score'], reverse=True)
    else:
        matched_results.sort(key=lambda x: x['foliux_score'], reverse=True)

    return {
        'raw_query': query_text,
        'tags': parsed['tags'],
        'results': matched_results,
        'total_count': len(matched_results),
    }
