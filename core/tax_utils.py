import logging
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from django.db import models
from .models import (
    UserTaxProfile, Dividend, PnLStatement, MFTransaction,
    CoinTransaction, NPSTransaction, FixedAsset, OtherAsset, CashFlowEntry
)

logger = logging.getLogger(__name__)

def fy_to_dates(fy_str):
    """
    Convert financial year string '2025-2026' to start and end dates.
    Returns (start_date, end_date)
    """
    try:
        parts = fy_str.split('-')
        start_year = int(parts[0].strip())
        end_year = int(parts[1].strip())
        return date(start_year, 4, 1), date(end_year, 3, 31)
    except Exception as e:
        logger.error(f"Error parsing FY string {fy_str}: {e}")
        # Default fallback to current/previous FY
        today = date.today()
        y = today.year
        if today.month < 4:
            y -= 1
        return date(y, 4, 1), date(y + 1, 3, 31)

def get_tax_portfolio_data(user, fy_str):
    """
    Automatically fetch all investment and income data from the user's FOLIUX portfolio.
    """
    start_date, end_date = fy_to_dates(fy_str)
    
    # 1. Salary & Business manual entries from Cashflow
    salary_cf = CashFlowEntry.objects.filter(
        user=user, entry_type='INCOME', category='SALARY', date__range=(start_date, end_date)
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    business_cf = CashFlowEntry.objects.filter(
        user=user, entry_type='INCOME', category='BUSINESS', date__range=(start_date, end_date)
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    other_income_cf = CashFlowEntry.objects.filter(
        user=user, entry_type='INCOME', category__in=['OTHER_INCOME', 'OTHER'], date__range=(start_date, end_date)
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    # 2. Rental Income
    rent_cf = CashFlowEntry.objects.filter(
        user=user, entry_type='INCOME', category='RENTAL_INCOME', date__range=(start_date, end_date)
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    other_assets = OtherAsset.objects.filter(user=user)
    rent_assets = Decimal('0')
    for asset in other_assets:
        monthly_rent = asset.monthly_rent or Decimal('0')
        if asset.purchase_date <= end_date and monthly_rent > 0:
            m_start = max(start_date, asset.purchase_date)
            # Months active in the financial year
            months_active = (end_date.year - m_start.year) * 12 + (end_date.month - m_start.month) + 1
            months_active = max(0, min(12, months_active))
            rent_assets += monthly_rent * months_active
            
    rental_income = rent_cf + rent_assets

    # 3. Fixed Deposit / RD Interest accrued in the FY
    fixed_assets = FixedAsset.objects.filter(user=user, investment_date__lte=end_date)
    fd_interest = Decimal('0')
    ppf_interest = Decimal('0')
    other_interest = Decimal('0')
    
    for asset in fixed_assets:
        val_end = asset.value_at_date(end_date)
        if asset.investment_date >= start_date:
            val_start = asset.invested_amount_decimal
        else:
            val_start = asset.value_at_date(start_date - timedelta(days=1))
            
        interest = val_end - val_start
        
        # Adjust for monthly RD/PPF deposits made during the year (which increase value but aren't interest)
        monthly_deposit = asset.monthly_deposit or Decimal('0')
        if asset.asset_type in ['RD', 'PPF', 'EPF'] and monthly_deposit > 0:
            dep_start = max(start_date, asset.investment_date)
            dep_end = min(end_date, asset.maturity_date) if asset.maturity_date else end_date
            if dep_end >= dep_start:
                months = (dep_end.year - dep_start.year) * 12 + (dep_end.month - dep_start.month) + 1
                interest -= monthly_deposit * months
                
        interest = max(Decimal('0'), interest)
        
        if asset.asset_type in ['FD', 'RD']:
            fd_interest += interest
        elif asset.asset_type in ['PPF', 'EPF']:
            ppf_interest += interest
        else:
            other_interest += interest

    # 4. Stock Dividends
    stock_dividends = Dividend.objects.filter(
        user=user, received_date__range=(start_date, end_date)
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    # 5. Mutual Fund Dividends (Cashflow category)
    mf_dividends = CashFlowEntry.objects.filter(
        user=user, entry_type='INCOME', category='DIVIDEND_INCOME', date__range=(start_date, end_date)
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    # 6. Stock Capital Gains (from PnLStatement)
    pnl_records = PnLStatement.objects.filter(user=user, exit_date__range=(start_date, end_date))
    stcg_equity = Decimal('0')
    ltcg_equity = Decimal('0')
    for p in pnl_records:
        if p.entry_date:
            holding_days = (p.exit_date - p.entry_date).days
            if holding_days <= 365:
                stcg_equity += p.realized_profit
            else:
                ltcg_equity += p.realized_profit
        else:
            stcg_equity += p.realized_profit # Default to short term if purchase date unknown

    # 7. Mutual Fund Capital Gains (dynamically computed via FIFO)
    mf_txs = MFTransaction.objects.filter(user=user).order_by('date', 'created_at')
    buy_lots = defaultdict(list)
    mf_stcg_equity = Decimal('0')
    mf_ltcg_equity = Decimal('0')
    mf_debt_gains = Decimal('0') # debt is taxed at slab rates
    
    for tx in mf_txs:
        fid = tx.fund_id
        fund_name = tx.fund.name.lower()
        is_equity = not any(w in fund_name for w in ['debt', 'liquid', 'gilt', 'treasury', 'money market', 'bond', 'corporate bond'])
        
        if tx.transaction_type == 'BUY':
            buy_lots[fid].append({'units': tx.units, 'price': tx.price, 'date': tx.date})
        elif tx.transaction_type == 'SELL':
            sell_units = tx.units
            cost = Decimal('0')
            lots_matched = []
            while sell_units > 0 and buy_lots[fid]:
                lot = buy_lots[fid][0]
                matched = min(lot['units'], sell_units)
                cost += matched * lot['price']
                lots_matched.append({'date': lot['date'], 'units': matched, 'price': lot['price']})
                lot['units'] -= matched
                sell_units -= matched
                if lot['units'] <= 0:
                    buy_lots[fid].pop(0)
            
            if start_date <= tx.date <= end_date:
                for lm in lots_matched:
                    lot_sale = lm['units'] * tx.price
                    lot_cost = lm['units'] * lm['price']
                    lot_gain = lot_sale - lot_cost
                    holding_days = (tx.date - lm['date']).days
                    if is_equity:
                        if holding_days <= 365:
                            mf_stcg_equity += lot_gain
                        else:
                            mf_ltcg_equity += lot_gain
                    else:
                        mf_debt_gains += lot_gain

    # Combine Stock and MF Equity Capital Gains
    total_stcg_equity = stcg_equity + mf_stcg_equity
    total_ltcg_equity = ltcg_equity + mf_ltcg_equity

    # 8. Crypto Capital Gains (FIFO)
    coin_txs = CoinTransaction.objects.filter(user=user).order_by('date', 'created_at')
    c_buy_lots = defaultdict(list)
    crypto_gains = Decimal('0')
    for tx in coin_txs:
        cid = tx.coin_id
        if tx.transaction_type == 'BUY':
            c_buy_lots[cid].append({'units': tx.units, 'price': tx.price, 'date': tx.date})
        elif tx.transaction_type == 'SELL':
            sell_units = tx.units
            cost = Decimal('0')
            while sell_units > 0 and c_buy_lots[cid]:
                lot = c_buy_lots[cid][0]
                matched = min(lot['units'], sell_units)
                cost += matched * lot['price']
                lot['units'] -= matched
                sell_units -= matched
                if lot['units'] <= 0:
                    c_buy_lots[cid].pop(0)
            
            if start_date <= tx.date <= end_date:
                tx_gain = (tx.units * tx.price) - cost
                if tx_gain > 0:
                    crypto_gains += tx_gain # 115BBH: no set-off, tax positive gains only

    # 9. NPS Contributions
    nps_txs = NPSTransaction.objects.filter(
        user=user, transaction_type='BUY', date__range=(start_date, end_date)
    )
    nps_contrib = sum(tx.units * tx.price for tx in nps_txs)

    # 10. PPF/EPF Contributions
    ppf_assets = FixedAsset.objects.filter(user=user, asset_type__in=['PPF', 'EPF'], investment_date__lte=end_date)
    ppf_contrib = Decimal('0')
    for asset in ppf_assets:
        monthly_deposit = asset.monthly_deposit or Decimal('0')
        if monthly_deposit > 0:
            m_start = max(start_date, asset.investment_date)
            m_end = min(end_date, asset.maturity_date) if asset.maturity_date else end_date
            if m_end >= m_start:
                months = (m_end.year - m_start.year) * 12 + (m_end.month - m_start.month) + 1
                ppf_contrib += monthly_deposit * months
                
    cf_ppf = CashFlowEntry.objects.filter(
        user=user, entry_type='INVESTMENT', category__in=['PPF', 'EPF'], date__range=(start_date, end_date)
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
    ppf_contrib += cf_ppf

    # 11. ELSS (Equity Linked Savings Schemes u/s 80C) from Mutual Fund BUYs during the year
    elss_contrib = Decimal('0')
    elss_txs = MFTransaction.objects.filter(
        user=user, transaction_type='BUY', date__range=(start_date, end_date)
    )
    for tx in elss_txs:
        if 'elss' in tx.fund.name.lower() or 'tax saver' in tx.fund.name.lower():
            elss_contrib += tx.units * tx.price

    return {
        'salary': salary_cf,
        'business_income': business_cf,
        'other_taxable_income': other_income_cf,
        'rental_income': rental_income,
        'fd_interest': fd_interest + other_interest,
        'stock_dividends': stock_dividends,
        'mf_dividends': mf_dividends,
        'stcg_equity': total_stcg_equity,
        'ltcg_equity': total_ltcg_equity,
        'crypto_gains': crypto_gains,
        'debt_gains': mf_debt_gains,
        'nps_contrib': nps_contrib,
        'ppf_contrib': ppf_contrib,
        'elss_contrib': elss_contrib,
    }

def calculate_taxes(state):
    """
    Calculate income tax under Old and New regimes.
    Input `state` should contain all merged portfolio + manual declarations.
    """
    d = lambda v: Decimal(str(v)) if v is not None else Decimal('0')
    
    # Inputs
    salary = d(state.get('salary'))
    business_income = d(state.get('business_income'))
    other_taxable_income = d(state.get('other_taxable_income'))
    agricultural_income = d(state.get('agricultural_income'))
    hra_received = d(state.get('hra_received'))
    rent_paid = d(state.get('rent_paid'))
    home_loan_interest = d(state.get('home_loan_interest'))
    
    # Deductions
    sec_80c = d(state.get('section_80c'))
    sec_80d = d(state.get('section_80d'))
    sec_80ccd1b = d(state.get('section_80ccd1b'))
    sec_80g = d(state.get('section_80g'))
    other_deductions = d(state.get('other_deductions'))

    # Portfolio Income
    rental_income = d(state.get('rental_income'))
    fd_interest = d(state.get('fd_interest'))
    stock_dividends = d(state.get('stock_dividends'))
    mf_dividends = d(state.get('mf_dividends'))
    debt_gains = d(state.get('debt_gains'))
    stcg_equity = d(state.get('stcg_equity'))
    ltcg_equity = d(state.get('ltcg_equity'))
    crypto_gains = d(state.get('crypto_gains'))
    
    # Portfolio auto-computed contributions (for old regime deductions)
    nps_contrib = d(state.get('nps_contrib'))
    ppf_contrib = d(state.get('ppf_contrib'))
    elss_contrib = d(state.get('elss_contrib'))

    # Standard Deductions
    std_deduction_old = min(salary, Decimal('50000'))
    std_deduction_new = min(salary, Decimal('75000'))

    # HRA Exemption u/s 10(13A) (Old Regime only)
    # Assumes basic salary = 50% of annual salary
    basic_salary = salary * Decimal('0.5')
    hra_exemption = Decimal('0')
    if basic_salary > 0 and hra_received > 0 and rent_paid > 0:
        hra_exemption = min(
            hra_received,
            max(Decimal('0'), rent_paid - (basic_salary * Decimal('0.1'))),
            basic_salary * Decimal('0.5')
        )

    # Net Rental Income (after 30% standard deduction u/s 24(a))
    # Old Regime: Can deduct Home Loan Interest (up to ₹2L u/s 24(b))
    net_rent_old = rental_income * Decimal('0.7')
    home_loan_interest_ded_old = min(home_loan_interest, Decimal('200000'))
    
    # New Regime: Standard 30% deduction is allowed, home loan interest is NOT allowed
    net_rent_new = rental_income * Decimal('0.7')

    # Old Regime Deductions
    ded_80c = min(sec_80c + ppf_contrib + elss_contrib, Decimal('150000'))
    ded_80d = min(sec_80d, Decimal('100000'))
    ded_80ccd1b = min(sec_80ccd1b + nps_contrib, Decimal('50000'))
    ded_80g = sec_80g
    ded_other = other_deductions

    # Gross Total Normal Income (normal rates)
    # Debt fund capital gains are taxed at slab rates
    normal_income_old = salary + business_income + other_taxable_income + net_rent_old + fd_interest + stock_dividends + mf_dividends + debt_gains
    normal_income_new = salary + business_income + other_taxable_income + net_rent_new + fd_interest + stock_dividends + mf_dividends + debt_gains

    # Net Taxable Normal Income
    taxable_normal_old = max(Decimal('0'), normal_income_old - std_deduction_old - hra_exemption - ded_80c - ded_80d - ded_80ccd1b - ded_80g - home_loan_interest_ded_old - ded_other)
    taxable_normal_new = max(Decimal('0'), normal_income_new - std_deduction_new)

    # 1. Tax on Normal Income (Slab rates)
    tax_normal_old = calc_slab_tax_old(taxable_normal_old)
    tax_normal_new = calc_slab_tax_new(taxable_normal_new)

    # 2. Capital Gains & Special Taxes
    tax_stcg_equity = stcg_equity * Decimal('0.20') # 20% Section 111A
    tax_ltcg_equity = max(Decimal('0'), ltcg_equity - Decimal('125000')) * Decimal('0.125') # 12.5% Section 112A (first 1.25L exempt)
    tax_crypto = crypto_gains * Decimal('0.30') # 30% Section 115BBH

    # Total Taxable Income
    total_taxable_old = taxable_normal_old + stcg_equity + ltcg_equity + crypto_gains
    total_taxable_new = taxable_normal_new + stcg_equity + ltcg_equity + crypto_gains

    # 3. Rebate u/s 87A
    # Old Regime: Rebate u/s 87A is available if net taxable income (excluding LTCG 112A) <= 5,00,000
    rebate_old = Decimal('0')
    if (total_taxable_old - ltcg_equity) <= Decimal('500000'):
        rebate_old = min(tax_normal_old + tax_stcg_equity, Decimal('12500'))

    # New Regime: Rebate u/s 87A is available if net taxable income (excluding LTCG 112A) <= 12,00,000
    # Capped at ₹60,000. Marginal relief applies if it slightly exceeds 12L.
    rebate_new = Decimal('0')
    taxable_income_for_rebate = total_taxable_new - ltcg_equity
    if taxable_income_for_rebate <= Decimal('1200000'):
        rebate_new = min(tax_normal_new + tax_stcg_equity, Decimal('60000'))
    else:
        # Marginal Relief: Tax payable (excluding tax on LTCG 112A + crypto) cannot exceed excess income
        base_tax = tax_normal_new + tax_stcg_equity
        excess_income = taxable_income_for_rebate - Decimal('1200000')
        if base_tax > excess_income:
            rebate_new = max(Decimal('0'), base_tax - excess_income)

    # Tax Payable Before Cess & Surcharge
    tax_payable_old = max(Decimal('0'), tax_normal_old + tax_stcg_equity - rebate_old) + tax_ltcg_equity + tax_crypto
    tax_payable_new = max(Decimal('0'), tax_normal_new + tax_stcg_equity - rebate_new) + tax_ltcg_equity + tax_crypto

    # 4. Surcharge Calculations
    # Surcharge on Dividend, STCG 111A, LTCG 112A is capped at 15%.
    # Surcharge slabs:
    # 50L - 1Cr: 10%
    # 1Cr - 2Cr: 15%
    # 2Cr - 5Cr: 25% (capped at 25% for New Regime)
    # >5Cr: 37% (Old Regime only)
    surcharge_old = calculate_surcharge(total_taxable_old, tax_payable_old, tax_normal_old, tax_stcg_equity, tax_ltcg_equity, is_new_regime=False)
    surcharge_new = calculate_surcharge(total_taxable_new, tax_payable_new, tax_normal_new, tax_stcg_equity, tax_ltcg_equity, is_new_regime=True)

    # 5. Cess: 4% of (Tax + Surcharge)
    cess_old = (tax_payable_old + surcharge_old) * Decimal('0.04')
    cess_new = (tax_payable_new + surcharge_new) * Decimal('0.04')

    final_tax_old = tax_payable_old + surcharge_old + cess_old
    final_tax_new = tax_payable_new + surcharge_new + cess_new

    # Recommendation
    recommended_regime = 'NEW' if final_tax_new <= final_tax_old else 'OLD'
    tax_saved = abs(final_tax_old - final_tax_new)

    # Suggestions (Old Regime planning opportunities)
    suggestions = []
    if final_tax_old > final_tax_new:
        remaining_80c = Decimal('150000') - ded_80c
        remaining_nps = Decimal('50000') - ded_80ccd1b
        
        if remaining_80c > 0:
            suggestions.append({
                'category': 'Section 80C',
                'description': f"Invest an additional ₹{remaining_80c:,.2f} in PPF, ELSS, or LIC to maximize your 80C deduction.",
                'potential_saving': float(remaining_80c * Decimal('0.312') if taxable_normal_old > 1000000 else remaining_80c * Decimal('0.208')) # approx tax rate
            })
        if remaining_nps > 0:
            suggestions.append({
                'category': 'Section 80CCD(1B)',
                'description': f"Contribute an additional ₹{remaining_nps:,.2f} to NPS (Tier 1) for a deduction over and above 80C.",
                'potential_saving': float(remaining_nps * Decimal('0.312') if taxable_normal_old > 1000000 else remaining_nps * Decimal('0.208'))
            })

    return {
        'total_income': float(normal_income_old + stcg_equity + ltcg_equity + crypto_gains),
        'regimes': {
            'old': {
                'gross_total': float(normal_income_old),
                'deductions': float(std_deduction_old + hra_exemption + ded_80c + ded_80d + ded_80ccd1b + ded_80g + home_loan_interest_ded_old + ded_other),
                'taxable_income': float(total_taxable_old),
                'taxable_normal': float(taxable_normal_old),
                'tax_on_normal': float(tax_normal_old),
                'tax_on_stcg': float(tax_stcg_equity),
                'tax_on_ltcg': float(tax_ltcg_equity),
                'tax_on_crypto': float(tax_crypto),
                'rebate': float(rebate_old),
                'surcharge': float(surcharge_old),
                'cess': float(cess_old),
                'total_tax': float(final_tax_old),
            },
            'new': {
                'gross_total': float(normal_income_new),
                'deductions': float(std_deduction_new),
                'taxable_income': float(total_taxable_new),
                'taxable_normal': float(taxable_normal_new),
                'tax_on_normal': float(tax_normal_new),
                'tax_on_stcg': float(tax_stcg_equity),
                'tax_on_ltcg': float(tax_ltcg_equity),
                'tax_on_crypto': float(tax_crypto),
                'rebate': float(rebate_new),
                'surcharge': float(surcharge_new),
                'cess': float(cess_new),
                'total_tax': float(final_tax_new),
            }
        },
        'recommended_regime': recommended_regime,
        'tax_saved': float(tax_saved),
        'suggestions': suggestions
    }

def calc_slab_tax_old(income):
    """Calculate normal slab tax under the Old Regime."""
    if income <= 250000:
        return Decimal('0')
    elif income <= 500000:
        return (income - Decimal('250000')) * Decimal('0.05')
    elif income <= 1000000:
        return Decimal('12500') + (income - Decimal('500000')) * Decimal('0.20')
    else:
        return Decimal('112500') + (income - Decimal('1000000')) * Decimal('0.30')

def calc_slab_tax_new(income):
    """Calculate normal slab tax under the New Regime (FY 2025-26 / FY 2026-27)."""
    if income <= 400000:
        return Decimal('0')
    elif income <= 800000:
        return (income - Decimal('400000')) * Decimal('0.05')
    elif income <= 1200000:
        return Decimal('20000') + (income - Decimal('800000')) * Decimal('0.10')
    elif income <= 1600000:
        return Decimal('60000') + (income - Decimal('1200000')) * Decimal('0.15')
    elif income <= 2000000:
        return Decimal('120000') + (income - Decimal('1600000')) * Decimal('0.20')
    elif income <= 2400000:
        return Decimal('200000') + (income - Decimal('2000000')) * Decimal('0.25')
    else:
        return Decimal('300000') + (income - Decimal('2400000')) * Decimal('0.30')

def calculate_surcharge(income, tax_payable, tax_normal, tax_stcg_equity, tax_ltcg_equity, is_new_regime=False):
    """Calculate surcharge accounting for 15% cap on capital gains/dividends tax."""
    if income <= Decimal('5000000'):
        return Decimal('0')
        
    # Surcharge rates
    if income <= Decimal('10000000'):
        rate_normal = Decimal('0.10')
    elif income <= Decimal('20000000'):
        rate_normal = Decimal('0.15')
    else:
        if is_new_regime:
            rate_normal = Decimal('0.25') # Max capped at 25% in new regime
        else:
            if income <= Decimal('50000000'):
                rate_normal = Decimal('0.25')
            else:
                rate_normal = Decimal('0.37') # 37% u/s old regime above 5Cr
                
    # Special capital gains tax surcharge is capped at 15%
    rate_special = min(rate_normal, Decimal('0.15'))
    
    # Distribute tax components
    tax_special = tax_stcg_equity + tax_ltcg_equity
    tax_normal_component = tax_payable - tax_special
    
    surcharge = (tax_normal_component * rate_normal) + (tax_special * rate_special)
    return surcharge
