from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from .models import Company, QuarterlyResult, ProfitLoss, BalanceSheet, CashFlow, ShareholdingPattern, CompanyDocument, HistoricalPrice

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
    
    # Peers: Companies in the same industry (including the current one for comparison in peers tab)
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
    })
