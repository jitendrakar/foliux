import os
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.db.models import Q, Avg, Sum, Count
from .models import (
    Company, QuarterlyResult, ProfitLoss, BalanceSheet, CashFlow, 
    ShareholdingPattern, CompanyDocument, HistoricalPrice,
    ManagementDocument, ManagementForecast, ForecastComparison, ManagementReliabilityScore
)

def screener_home(request):
    # Fetch some popular companies to show on the homepage
    popular_companies = Company.objects.all()[:6]
    return render(request, 'screener/home.html', {
        'popular_companies': popular_companies
    })

def screener_suggest(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)
    
    # Filter by name, nse symbol, or bse symbol
    results = Company.objects.filter(
        Q(name__icontains=query) |
        Q(nse_symbol__icontains=query) |
        Q(bse_symbol__icontains=query)
    )[:10]
    
    data = []
    for c in results:
        data.append({
            'name': c.name,
            'nse_symbol': c.nse_symbol,
            'bse_symbol': c.bse_symbol or '',
            'industry': c.industry or ''
        })
    
    return JsonResponse(data, safe=False)

def company_detail(request, symbol):
    # Retrieve the company by NSE or BSE symbol
    company = get_object_or_404(Company, Q(nse_symbol__iexact=symbol) | Q(bse_symbol__iexact=symbol))
    
    # Retrieve financial details
    quarterly_results = company.quarterly_results.all()
    yearly_financials = company.yearly_financials.all()
    balance_sheets = company.balance_sheets.all()
    cash_flows = company.cash_flows.all()
    shareholdings = company.shareholdings.all()
    documents = company.documents.all()
    
    # Management Forecast vs Achievement Details
    reliability_score = getattr(company, 'reliability_score', None)
    management_forecasts = company.management_forecasts.select_related('comparison', 'document').all()
    management_documents = company.management_documents.all()

    # Peers: Companies in the same industry
    peers = Company.objects.filter(industry=company.industry)
    
    # Historical Prices for chart
    prices_qs = company.historical_prices.all().order_by('date')
    historical_data = []
    for p in prices_qs:
        historical_data.append({
            'time': p.date.strftime('%Y-%m-%d'),
            'open': float(p.open_price),
            'high': float(p.high_price),
            'low': float(p.low_price),
            'close': float(p.close_price),
            'volume': int(p.volume)
        })
        
    return render(request, 'screener/company_detail.html', {
        'company': company,
        'quarterly_results': quarterly_results,
        'yearly_financials': yearly_financials,
        'balance_sheets': balance_sheets,
        'cash_flows': cash_flows,
        'shareholdings': shareholdings,
        'documents': documents,
        'peers': peers,
        'historical_data': historical_data,
        'reliability_score': reliability_score,
        'management_forecasts': management_forecasts,
        'management_documents': management_documents,
    })


def management_credibility_dashboard(request):
    """
    Global Management Forecast vs. Achievement Credibility Dashboard.
    Provides filtering by company, sector, industry, status, and reliability score.
    """
    query = request.GET.get('q', '').strip()
    sector_filter = request.GET.get('sector', '').strip()
    industry_filter = request.GET.get('industry', '').strip()
    status_filter = request.GET.get('status', '').strip()
    min_score = request.GET.get('min_score', '').strip()
    sort_by = request.GET.get('sort', 'score_desc')

    scores_qs = ManagementReliabilityScore.objects.select_related('company').all()

    if query:
        scores_qs = scores_qs.filter(
            Q(company__name__icontains=query) | Q(company__nse_symbol__icontains=query)
        )

    if sector_filter:
        scores_qs = scores_qs.filter(company__sector__iexact=sector_filter)

    if industry_filter:
        scores_qs = scores_qs.filter(company__industry__iexact=industry_filter)

    if min_score and min_score.isdigit():
        scores_qs = scores_qs.filter(overall_score__gte=int(min_score))

    if sort_by == 'score_asc':
        scores_qs = scores_qs.order_by('overall_score')
    elif sort_by == 'reliability_desc':
        scores_qs = scores_qs.order_by('-reliability_score_percent')
    elif sort_by == 'delay_desc':
        scores_qs = scores_qs.order_by('-avg_delay_months')
    else:
        scores_qs = scores_qs.order_by('-overall_score', '-reliability_score_percent')

    # Aggregated Scorecard Stats
    total_companies = scores_qs.count()
    avg_score = scores_qs.aggregate(Avg('overall_score'))['overall_score__avg'] or 0.0
    total_forecasts = scores_qs.aggregate(Sum('total_forecasts'))['total_forecasts__sum'] or 0
    total_achieved = scores_qs.aggregate(Sum('achieved_count'))['achieved_count__sum'] or 0
    total_delayed = scores_qs.aggregate(Sum('delayed_count'))['delayed_count__sum'] or 0

    achieved_pct = round((total_achieved / total_forecasts * 100), 1) if total_forecasts > 0 else 0.0

    # Sector & Industry options for sidebar filters
    available_sectors = Company.objects.exclude(sector='').values_list('sector', flat=True).distinct()
    available_industries = Company.objects.exclude(industry='').values_list('industry', flat=True).distinct()

    # Recent Forecast Comparisons table
    recent_comparisons = ForecastComparison.objects.select_related('forecast', 'forecast__company', 'forecast__document').all()
    if status_filter:
        recent_comparisons = recent_comparisons.filter(status__iexact=status_filter)
    recent_comparisons = recent_comparisons[:25]

    return render(request, 'screener/management_credibility.html', {
        'scores': scores_qs,
        'total_companies': total_companies,
        'avg_score': round(avg_score, 1),
        'total_forecasts': total_forecasts,
        'total_achieved': total_achieved,
        'achieved_pct': achieved_pct,
        'total_delayed': total_delayed,
        'available_sectors': available_sectors,
        'available_industries': available_industries,
        'recent_comparisons': recent_comparisons,
        'query': query,
        'sector_filter': sector_filter,
        'industry_filter': industry_filter,
        'status_filter': status_filter,
        'min_score': min_score,
        'sort_by': sort_by,
    })


def serve_local_document(request, doc_id):
    """
    Serves downloaded local PDF/text file from result/<SYMBOL>/<FY>/ repository
    for in-browser PDF viewing or direct download.
    """
    doc = get_object_or_404(ManagementDocument, id=doc_id)
    filepath = doc.local_file_path

    if not os.path.exists(filepath):
        raise Http404(f"Document file not found at local storage: {filepath}")

    response = FileResponse(open(filepath, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{os.path.basename(filepath)}"'
    return response


# --- Natural Language Query Search Views ---

def nl_search_view(request):
    """
    AI-Powered Natural Language Query Search Page.
    Handles plain English prompts e.g. 'PE Ratio below 50, ROE above 20%, Management Reliability above 80%'.
    """
    query_text = request.GET.get('q', '').strip()
    if not query_text:
        query_text = "PE Ratio below 50, ROE above 20%, and Management Reliability Score above 80%"

    from screener.nl_query_engine import execute_nl_query
    query_result = execute_nl_query(query_text)

    # Preset sample prompts for quick click-to-run
    sample_queries = [
        "PE Ratio below 50",
        "PE Ratio between 10 and 25",
        "ROE greater than 20%",
        "ROCE above 18%",
        "Debt to Equity below 0.50",
        "Market Cap above 10,000 Crore",
        "Sales Growth above 15%",
        "Profit Growth above 20%",
        "Dividend Yield above 2%",
        "Promoter Holding above 60%",
        "Low Debt Companies",
        "Management Reliability Score above 80%",
        "Forecast Achievement above 50%",
        "Companies with no delayed projects",
        "Highest management credibility",
        "PE below 25, Debt below 0.5, and Forecast Achievement above 75%",
    ]

    return render(request, 'screener/nl_search_results.html', {
        'query_text': query_text,
        'tags': query_result['tags'],
        'results': query_result['results'],
        'total_count': query_result['total_count'],
        'sample_queries': sample_queries,
    })


def nl_search_api(request):
    """JSON API endpoint for Natural Language Query Execution."""
    query_text = request.GET.get('q', '').strip()
    if not query_text:
        return JsonResponse({'error': 'Query parameter q is required.'}, status=400)

    from screener.nl_query_engine import execute_nl_query
    query_result = execute_nl_query(query_text)
    return JsonResponse(query_result)


def nl_suggest_api(request):
    """JSON API endpoint for Natural Language Query Autocomplete & Smart Suggestions."""
    q = request.GET.get('q', '').strip().lower()
    
    predefined_suggestions = [
        "PE Ratio below 50",
        "PE Ratio between 10 and 25",
        "ROE greater than 20%",
        "ROCE above 18%",
        "Debt to Equity below 0.50",
        "Market Cap above 10,000 Crore",
        "Sales Growth above 15%",
        "Profit Growth above 20%",
        "Dividend Yield above 2%",
        "Promoter Holding above 60%",
        "Low Debt Companies",
        "Companies making new 52-week highs",
        "Management Reliability Score above 80%",
        "Management Forecast Achievement above 50%",
        "Companies that delivered all promised CAPEX",
        "Companies with no delayed projects",
        "Highest management credibility",
        "Small Cap companies with Management Reliability above 80%",
        "PE below 25, Debt below 0.5, and Forecast Achievement above 75%",
    ]

    if not q:
        suggestions = predefined_suggestions[:6]
    else:
        suggestions = [s for s in predefined_suggestions if q in s.lower()]
        if not suggestions:
            # Also search company names
            company_matches = Company.objects.filter(
                Q(name__icontains=q) | Q(nse_symbol__icontains=q)
            )[:4]
            for c in company_matches:
                suggestions.append(f"{c.name} ({c.nse_symbol})")

    return JsonResponse({'suggestions': suggestions[:8]})


