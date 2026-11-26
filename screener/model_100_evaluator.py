import os
from screener.models import Company, ManagementForecast, ManagementReliabilityScore

def compute_100_point_model(company: Company, reliability_pct: float, delayed_count: int, avg_delay_months: float) -> dict:
    # 1. Management integrity and guidance delivery (Weight: 15)
    score_mgmt = round((float(reliability_pct) / 100.0) * 15.0, 1)

    # 2. Revenue growth consistency (Weight: 10)
    sg = float(company.sales_growth) if company.sales_growth else 12.0
    if sg >= 20.0:
        score_rev = 10.0
    elif sg >= 14.0:
        score_rev = 8.5
    elif sg >= 8.0:
        score_rev = 7.0
    elif sg >= 3.0:
        score_rev = 5.0
    elif sg >= 0.0:
        score_rev = 3.5
    else:
        score_rev = 2.0

    # 3. PAT growth and earnings quality (Weight: 10)
    pg = float(company.profit_growth) if company.profit_growth else 14.0
    if pg >= 22.0:
        score_pat = 10.0
    elif pg >= 15.0:
        score_pat = 8.5
    elif pg >= 8.0:
        score_pat = 7.0
    elif pg >= 0.0:
        score_pat = 5.0
    else:
        score_pat = 2.0

    # 4. Operating cash flow and free cash flow (Weight: 12)
    cf_records = company.cash_flows.all() if hasattr(company, 'cash_flows') else []
    if cf_records.exists():
        pos_cf = cf_records.filter(operating_cash__gt=0).count()
        ratio = pos_cf / cf_records.count() if cf_records.count() > 0 else 0.8
        score_cf = round(ratio * 12.0, 1)
    else:
        score_cf = 10.5 if (company.profit_growth and float(company.profit_growth) >= 10.0) else 8.5

    # 5. Return on equity and return on capital (Weight: 10)
    roe = float(company.roe) if company.roe else 15.0
    roce = float(company.roce) if company.roce else 16.0
    avg_ret = (roe + roce) / 2.0
    if avg_ret >= 22.0:
        score_ret = 10.0
    elif avg_ret >= 17.0:
        score_ret = 8.5
    elif avg_ret >= 12.0:
        score_ret = 7.0
    elif avg_ret >= 8.0:
        score_ret = 5.0
    else:
        score_ret = 3.0

    # 6. Debt and balance-sheet strength (Weight: 10)
    debt = float(company.debt) if company.debt else 0.0
    cash = float(company.cash) if company.cash else 0.0
    mcap = float(company.market_cap) if company.market_cap and company.market_cap > 0 else 5000.0
    net_debt = debt - cash
    if net_debt <= 0:
        score_bs = 10.0  # Zero Debt / Net Cash
    else:
        d_ratio = debt / mcap
        if d_ratio <= 0.15:
            score_bs = 8.5
        elif d_ratio <= 0.35:
            score_bs = 7.0
        elif d_ratio <= 0.60:
            score_bs = 5.0
        else:
            score_bs = 3.0

    # 7. Competitive advantage and market position (Weight: 10)
    if mcap >= 50000.0 and roce >= 15.0:
        score_moat = 10.0
    elif mcap >= 15000.0:
        score_moat = 8.5
    elif roe >= 18.0:
        score_moat = 8.0
    else:
        score_moat = 6.5

    # 8. Capital allocation and project execution (Weight: 10)
    if delayed_count == 0 and roce >= 15.0:
        score_cap_alloc = 10.0
    elif delayed_count <= 1:
        score_cap_alloc = 8.0
    elif delayed_count <= 2:
        score_cap_alloc = 6.5
    else:
        score_cap_alloc = 4.5

    # 9. Future growth opportunities (Weight: 8)
    growth_sectors = ['technology', 'healthcare', 'consumer', 'industrials', 'infrastructure', 'renewable']
    sec = (company.sector or '').lower()
    ind = (company.industry or '').lower()
    if any(s in sec or s in ind for s in growth_sectors):
        score_growth = 7.5 if sg >= 12.0 else 6.5
    else:
        score_growth = 6.0

    # 10. Corporate governance and shareholder treatment (Weight: 5)
    prom_h = float(company.promoter_holding) if company.promoter_holding else 50.0
    div_y = float(company.dividend_yield) if company.dividend_yield else 0.5
    if prom_h >= 50.0 and div_y > 0.2:
        score_gov = 5.0
    elif prom_h >= 40.0:
        score_gov = 4.0
    else:
        score_gov = 3.0

    total_score = round(
        score_mgmt + score_rev + score_pat + score_cf + score_ret +
        score_bs + score_moat + score_cap_alloc + score_growth + score_gov,
        1
    )
    final_score_int = int(round(total_score))

    breakdown = {
        'management_delivery': {'weight': 15, 'score': score_mgmt, 'label': 'Management integrity and guidance delivery'},
        'revenue_growth': {'weight': 10, 'score': score_rev, 'label': 'Revenue growth consistency'},
        'pat_growth': {'weight': 10, 'score': score_pat, 'label': 'PAT growth and earnings quality'},
        'cash_flow': {'weight': 12, 'score': score_cf, 'label': 'Operating cash flow and free cash flow'},
        'roe_roce': {'weight': 10, 'score': score_ret, 'label': 'Return on equity and return on capital'},
        'balance_sheet': {'weight': 10, 'score': score_bs, 'label': 'Debt and balance-sheet strength'},
        'competitive_advantage': {'weight': 10, 'score': score_moat, 'label': 'Competitive advantage and market position'},
        'capital_allocation': {'weight': 10, 'score': score_cap_alloc, 'label': 'Capital allocation and project execution'},
        'growth_opportunities': {'weight': 8, 'score': score_growth, 'label': 'Future growth opportunities'},
        'governance': {'weight': 5, 'score': score_gov, 'label': 'Corporate governance and shareholder treatment'},
        'total': {'weight': 100, 'score': total_score, 'overall_int': final_score_int}
    }

    return {
        'score_mgmt_delivery': score_mgmt,
        'score_revenue_growth': score_rev,
        'score_pat_growth': score_pat,
        'score_cash_flow': score_cf,
        'score_roe_roce': score_ret,
        'score_balance_sheet': score_bs,
        'score_competitive_advantage': score_moat,
        'score_capital_allocation': score_cap_alloc,
        'score_growth_opportunities': score_growth,
        'score_governance': score_gov,
        'total_score': total_score,
        'overall_score_int': final_score_int,
        'breakdown': breakdown,
    }
