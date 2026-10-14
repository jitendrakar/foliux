"""
FOLIUX AI Audio & Voice Investment Adviser Engine.
Provides rule-based portfolio allocation and execution guidance
with dual output: rich structured text & natural speech synthesis text.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

def parse_advisory_query(query: str) -> Dict[str, Any]:
    """
    Parses natural language query to extract investment amount, frequency,
    risk profile, horizon, and target asset interests.
    """
    q = query.lower().strip()
    
    # 1. Amount Extraction
    amount: Optional[float] = None
    amount_str = ""
    
    # Check for words like "1 lakh", "50k", "10,000", "5000", "1 crore"
    lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b', q)
    crore_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:crore|crores|cr)\b', q)
    k_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|thousand)\b', q)
    number_match = re.search(r'(?:rs\.?|inr|₹)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,8})', q)
    
    if crore_match:
        val = float(crore_match.group(1))
        amount = val * 10000000
        amount_str = f"₹{val:g} Crore"
    elif lakh_match:
        val = float(lakh_match.group(1))
        amount = val * 100000
        amount_str = f"₹{val:g} Lakh"
    elif k_match:
        val = float(k_match.group(1))
        amount = val * 1000
        amount_str = f"₹{val:g},000"
    elif number_match:
        raw_num = number_match.group(1).replace(',', '')
        amount = float(raw_num)
        amount_str = f"₹{amount:,.0f}"

    # Text number words fallback
    if amount is None:
        word_numbers = {
            "five thousand": 5000,
            "ten thousand": 10000,
            "fifteen thousand": 15000,
            "twenty thousand": 20000,
            "twenty five thousand": 25000,
            "thirty thousand": 30000,
            "fifty thousand": 50000,
            "one lakh": 100000,
            "two lakh": 200000,
            "five lakh": 500000,
            "ten lakh": 1000000,
        }
        for words, val in word_numbers.items():
            if words in q:
                amount = float(val)
                amount_str = f"₹{val:,.0f}"
                break

    # 2. Mode / Frequency (SIP vs Lump Sum)
    is_sip = any(term in q for term in ['sip', 'monthly', 'month', 'every month', 'per month', 'recurring', 'salary', 'each month', 'weekly'])
    is_lump_sum = any(term in q for term in ['lump sum', 'lumpsum', 'one time', 'one-time', 'single', 'corpus', 'bonus', 'savings currently'])
    
    # If not explicitly stated, infer based on amount
    if not is_sip and not is_lump_sum:
        if amount and amount <= 30000:
            is_sip = True
        elif amount and amount >= 100000:
            is_lump_sum = True
        else:
            is_sip = True  # Default to disciplined SIP

    # 3. Horizon / Duration
    horizon = "long" # default
    if any(term in q for term in ['short term', 'few months', '6 months', '1 year', 'emergency', 'quick', 'immediate', 'liquid']):
        horizon = "short"
    elif any(term in q for term in ['2 years', '3 years', 'medium term', '4 years', 'car', 'house downpayment']):
        horizon = "medium"
    elif any(term in q for term in ['5 years', '10 years', '15 years', '20 years', 'retirement', 'retire', 'pension', 'wealth', 'long term', 'compounding']):
        horizon = "long"

    # 4. Risk Profile
    risk = "moderate"
    if any(term in q for term in ['safe', 'low risk', 'no risk', 'conservative', 'guaranteed', 'capital protection', 'secure', 'senior citizen', 'fd']):
        risk = "conservative"
    elif any(term in q for term in ['high risk', 'aggressive', 'high return', 'maximum profit', 'multibagger', 'growth', 'smallcap', 'crypto']):
        risk = "aggressive"
    elif any(term in q for term in ['balanced', 'moderate', 'medium risk', 'reasonable', 'stable growth']):
        risk = "moderate"

    # 5. Asset Specific Interests
    assets_mentioned = []
    if any(w in q for w in ['stock', 'stocks', 'equity', 'shares']):
        assets_mentioned.append('stocks')
    if any(w in q for w in ['mutual fund', 'mutual funds', 'mf']):
        assets_mentioned.append('mutual_funds')
    if any(w in q for w in ['etf', 'index fund', 'niftybees', 'juniorbees', 'index']):
        assets_mentioned.append('etfs')
    if any(w in q for w in ['nps', 'pension', 'national pension system', '80ccd']):
        assets_mentioned.append('nps')
    if any(w in q for w in ['gold', 'sgb', 'silver', 'sovereign gold']):
        assets_mentioned.append('gold')
    if any(w in q for w in ['fd', 'fixed deposit', 'debt', 'liquid fund', 'arbitrage']):
        assets_mentioned.append('debt')
    if any(w in q for w in ['crypto', 'coin', 'bitcoin']):
        assets_mentioned.append('crypto')
    if any(w in q for w in ['ipo', 'listing gain']):
        assets_mentioned.append('ipo')

    # 6. Specific Topics
    topic = "general_advice"
    if 'retire' in q or 'retirement' in q or 'pension' in q:
        topic = "retirement"
    elif 'beginner' in q or 'starting' in q or 'first time' in q or 'new to investing' in q or 'start investing' in q:
        topic = "beginner"
    elif 'gold' in q and len(assets_mentioned) == 1:
        topic = "gold_focused"
    elif 'tax' in q or '80c' in q or 'elss' in q:
        topic = "tax_saving"
    elif 'ipo' in q:
        topic = "ipo_guidance"
    elif 'rules' in q or 'strategy' in q or '5%' in q or 'harvest' in q or 'fifo' in q:
        topic = "foliux_strategy"

    return {
        'raw_query': query,
        'amount': amount,
        'amount_str': amount_str,
        'is_sip': is_sip,
        'is_lump_sum': is_lump_sum,
        'horizon': horizon,
        'risk': risk,
        'assets_mentioned': assets_mentioned,
        'topic': topic
    }


def generate_investment_advice(query: str, market_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generates rule-based, institutional-grade investment advice tailored for FOLIUX users.
    Returns both rich visual data (allocations, execution steps) and clean spoken audio text.
    """
    parsed = parse_advisory_query(query)
    amount = parsed['amount']
    amount_str = parsed['amount_str']
    is_sip = parsed['is_sip']
    is_lump_sum = parsed['is_lump_sum']
    horizon = parsed['horizon']
    risk = parsed['risk']
    topic = parsed['topic']
    
    # Nifty 50 reference if available
    nifty_info = ""
    if market_context and market_context.get('nifty_price'):
        nifty_price = market_context.get('nifty_price')
        nifty_change = market_context.get('nifty_change', '')
        nifty_info = f"With Nifty 50 currently trading around {nifty_price} ({nifty_change}), "

    # -------------------------------------------------------------
    # 1. SPECIAL TOPIC: BEGINNER / FIRST-TIME INVESTOR
    # -------------------------------------------------------------
    if topic == "beginner":
        title = "Beginner's Rule-Based Wealth Architecture"
        mode_label = "SIP" if is_sip else "Staggered Deployment"
        
        allocations = [
            {
                'category': 'Broad Index ETFs (Nifty 50 & Next 50)',
                'percentage': 50,
                'color': '#2563eb',
                'icon': 'fas fa-chart-line',
                'instruments': ['NIFTYBEES', 'JUNIORBEES'],
                'rationale': 'Low-cost (0.05% expense ratio) access to India’s top 100 blue chips without single-stock risk.'
            },
            {
                'category': 'Flexi-Cap / Active Mutual Funds',
                'percentage': 25,
                'color': '#8b5cf6',
                'icon': 'fas fa-layer-group',
                'instruments': ['Parag Parikh Flexi Cap', 'HDFC Balanced Advantage'],
                'rationale': 'Professional active management across market caps with downside cushion.'
            },
            {
                'category': 'Gold Hedge (Sovereign Gold / ETF)',
                'percentage': 10,
                'color': '#f59e0b',
                'icon': 'fas fa-coins',
                'instruments': ['GOLDBEES', 'Sovereign Gold Bonds'],
                'rationale': 'Hedge against rupee depreciation and inflation cycles.'
            },
            {
                'category': 'Emergency Liquid Buffer / High-Yield FD',
                'percentage': 15,
                'color': '#10b981',
                'icon': 'fas fa-shield-alt',
                'instruments': ['Liquid Mutual Funds', 'Auto-sweep Savings / FD'],
                'rationale': 'Guaranteed liquidity so you never sell equity during a market drawdown.'
            }
        ]

        execution_steps = [
            {
                'step_num': 1,
                'title': 'Build 3-Month Emergency Reserve First',
                'detail': 'Before investing in equities, ensure 3 to 6 months of living expenses are in a liquid fund or savings account.',
                'icon': 'fas fa-shield-alt'
            },
            {
                'step_num': 2,
                'title': 'Automate Salary-Day SIPs',
                'detail': 'Schedule automated SIP debits between the 1st and 5th of each month right after salary credit.',
                'icon': 'fas fa-calendar-check'
            },
            {
                'step_num': 3,
                'title': 'Deploy Foliux Buy-on-Dips Pyramiding',
                'detail': 'When Nifty drops 3% to 5% from monthly peaks, deploy additional small opportunistic tranches.',
                'icon': 'fas fa-arrow-trend-down'
            },
            {
                'step_num': 4,
                'title': 'Harvest Profits at 22%',
                'detail': 'When any equity or mutual fund lot generates 20% to 22% unrealized profit, harvest gains and rebalance.',
                'icon': 'fas fa-hand-holding-dollar'
            }
        ]

        spoken_text = (
            f"Welcome to FOLIUX. For a beginner {mode_label} investment "
            f"{'of ' + amount_str if amount_str else ''}, here is your disciplined plan. "
            "Allocate 50 percent to broad market index ETFs like NIFTYBEES and JUNIORBEES for rock-solid large-cap growth. "
            "Allocate 25 percent to disciplined Flexi-Cap mutual funds. "
            "Keep 10 percent in Gold ETFs for inflation protection, and hold 15 percent in emergency liquid funds. "
            "Most importantly, follow the core Foliux rule: never try to time the market with emotions. "
            "Automate your investments right after salary day, accumulate incrementally during 3 to 5 percent market dips, "
            "and harvest profits when holdings reach a 22 percent target gain."
        )

        summary_text = (
            "For first-time investors, the winning formula is **low fees, maximum diversification, and disciplined automation**. "
            "Avoid speculative stock-picking until you build a solid index and mutual fund foundation."
        )

    # -------------------------------------------------------------
    # 2. SPECIAL TOPIC: RETIREMENT & PENSION (NPS FOCUS)
    # -------------------------------------------------------------
    elif topic == "retirement" or horizon == "long" and any(w in query.lower() for w in ['retire', 'pension', 'nps', 'old age']):
        title = "Long-Term Retirement & Compounding Blueprint"
        
        allocations = [
            {
                'category': 'National Pension System (Tier-1 Scheme E/C/G)',
                'percentage': 30,
                'color': '#f59e0b',
                'icon': 'fas fa-university',
                'instruments': ['NPS Scheme E (75% Equity)', 'NPS Scheme C (Corporate Bonds)'],
                'rationale': 'Unbeatable tax advantage under Section 80CCD(1B) plus ultra-low 0.09% fund management charges.'
            },
            {
                'category': 'Broad Index & Sectoral ETFs (Compounding Alpha)',
                'percentage': 40,
                'color': '#2563eb',
                'icon': 'fas fa-chart-line',
                'instruments': ['NIFTYBEES', 'MON100', 'ITBEES'],
                'rationale': 'Captures secular Indian & global technology growth over a 10 to 20 year compounding horizon.'
            },
            {
                'category': 'Consistent Flexi-Cap & Midcap SIPs',
                'percentage': 20,
                'color': '#8b5cf6',
                'icon': 'fas fa-layer-group',
                'instruments': ['HDFC Flexi Cap', 'Mirae Asset Large & Midcap'],
                'rationale': 'High-conviction equity exposure to beat headline retail inflation.'
            },
            {
                'category': 'Sovereign Gold / G-Secs',
                'percentage': 10,
                'color': '#10b981',
                'icon': 'fas fa-coins',
                'instruments': ['GOLDBEES', 'Target Maturity Govt Debt Funds'],
                'rationale': 'Defensive capital preservation against macro currency volatility.'
            }
        ]

        execution_steps = [
            {
                'step_num': 1,
                'title': 'Maximize Tier-1 NPS ₹50,000 Tax Benefit',
                'detail': 'Claim exclusive tax deduction under Section 80CCD(1B) over and above Section 80C limits.',
                'icon': 'fas fa-file-invoice-dollar'
            },
            {
                'step_num': 2,
                'title': 'Adopt Auto-Choice Active Lifecycle',
                'detail': 'Maintain 75% equity exposure in NPS during your accumulation years (20s to 40s) and gradually taper near retirement.',
                'icon': 'fas fa-sliders'
            },
            {
                'step_num': 3,
                'title': 'Run 10% Annual SIP Step-Up',
                'detail': 'Increase your monthly investment SIP by 10% each year as your income grows to double your retirement corpus.',
                'icon': 'fas fa-arrow-trend-up'
            },
            {
                'step_num': 4,
                'title': 'Rebalance Annually via FIFO',
                'detail': 'Use Foliux FIFO lot tracking to rebalance assets without incurring unnecessary Short Term Capital Gains tax.',
                'icon': 'fas fa-scale-balanced'
            }
        ]

        spoken_text = (
            f"Here is your FOLIUX retirement and wealth compounding strategy{' for ' + amount_str if amount_str else ''}. "
            "For a long-term retirement horizon, allocate 30 percent to the National Pension System Scheme E and C, "
            "which gives you unmatched tax deductions under Section 80CCD and ultra-low compounding fees. "
            "Place 40 percent in core index ETFs like NIFTYBEES and MON100, 20 percent in flexi-cap mutual fund SIPs, "
            "and 10 percent in Gold. Step up your monthly contributions by 10 percent every year. "
            "By letting compounding work over 10 to 15 years and avoiding emotional withdrawals, you create enduring wealth."
        )

        summary_text = (
            "Retirement wealth is built on **tax-advantaged compounding and disciplined step-up investing**. "
            "Combining Tier-1 NPS with core index ETFs delivers institutional-grade capital growth with maximum tax efficiency."
        )

    # -------------------------------------------------------------
    # 3. SPECIAL TOPIC: SHORT-TERM / CONSERVATIVE (SAFE CAPITAL)
    # -------------------------------------------------------------
    elif horizon == "short" or risk == "conservative":
        title = "Capital Preservation & Liquid Yield Strategy"
        
        allocations = [
            {
                'category': 'High-Yield Fixed Deposits / Bank Auto-Sweep',
                'percentage': 40,
                'color': '#10b981',
                'icon': 'fas fa-building-columns',
                'instruments': ['Scheduled Commercial Bank FDs (7.0 - 7.5%)', 'Auto-sweep'],
                'rationale': 'Guaranteed capital safety with predictable interest returns under DICGC insurance.'
            },
            {
                'category': 'Arbitrage & Liquid Mutual Funds',
                'percentage': 35,
                'color': '#3b82f6',
                'icon': 'fas fa-water',
                'instruments': ['Kotak Arbitrage Fund', 'ICICI Prudential Liquid Fund'],
                'rationale': 'Equity-taxed low-volatility returns with instant T+1 redemption liquidity.'
            },
            {
                'category': 'Short-Duration / Corporate Debt Funds',
                'percentage': 15,
                'color': '#6366f1',
                'icon': 'fas fa-receipt',
                'instruments': ['AAA Corporate Bond Funds', 'Treasury Bill Funds'],
                'rationale': 'Stable yields with minimal interest rate duration risk.'
            },
            {
                'category': 'Conservative Large-Cap ETF Buffer',
                'percentage': 10,
                'color': '#f59e0b',
                'icon': 'fas fa-chart-pie',
                'instruments': ['NIFTYBEES'],
                'rationale': 'Small growth kicker only if your horizon stretches beyond 12 months.'
            }
        ]

        execution_steps = [
            {
                'step_num': 1,
                'title': 'Never Risk Short-Term Capital in Mid/Small Caps',
                'detail': 'Money needed within 12 to 18 months must never be subjected to equity market volatility.',
                'icon': 'fas fa-ban'
            },
            {
                'step_num': 2,
                'title': 'Utilize Arbitrage Funds for Tax Efficiency',
                'detail': 'Arbitrage funds offer debt-like safety but are taxed as equity, saving taxes for high-bracket earners.',
                'icon': 'fas fa-percent'
            },
            {
                'step_num': 3,
                'title': 'Ladder Your Fixed Deposits',
                'detail': 'Split FDs into 3-month, 6-month, and 12-month tranches to maintain regular cashflow flexibility.',
                'icon': 'fas fa-bars-staggered'
            }
        ]

        spoken_text = (
            f"For capital safety and short-term horizons{' with ' + amount_str if amount_str else ''}, "
            "capital preservation is paramount. Do not deploy this money into volatile equities. "
            "Allocate 40 percent to scheduled bank fixed deposits yielding 7 to 7.5 percent. "
            "Place 35 percent in arbitrage and liquid mutual funds for tax-efficient liquidity, "
            "15 percent in AAA corporate bond funds, and keep no more than 10 percent in index ETFs. "
            "This protects your principal while beating ordinary savings rates."
        )

        summary_text = (
            "When your goal is within 1 to 2 years, **rule number one is capital protection**. "
            "High-yielding fixed deposits and arbitrage funds guarantee you will have the cash when you need it."
        )

    # -------------------------------------------------------------
    # 4. LUMP SUM INVESTMENT (DEPLOYMENT LOGIC)
    # -------------------------------------------------------------
    elif is_lump_sum and amount and amount >= 50000:
        title = f"Disciplined Deployment Plan for {amount_str} Lump Sum"
        
        allocations = [
            {
                'category': 'Core Index & Thematic ETFs (Nifty & Tech)',
                'percentage': 45,
                'color': '#2563eb',
                'icon': 'fas fa-chart-line',
                'instruments': ['NIFTYBEES (25%)', 'JUNIORBEES (10%)', 'ITBEES (10%)'],
                'rationale': 'Staggered STP entry into India’s dominant economic engines.'
            },
            {
                'category': 'Active Flexi-Cap & Midcap Funds',
                'percentage': 25,
                'color': '#8b5cf6',
                'icon': 'fas fa-layer-group',
                'instruments': ['Parag Parikh Flexi Cap', 'Motilal Oswal Midcap'],
                'rationale': 'Generates alpha through high-conviction corporate earnings growth.'
            },
            {
                'category': 'Sovereign Gold / Commodities',
                'percentage': 15,
                'color': '#f59e0b',
                'icon': 'fas fa-coins',
                'instruments': ['GOLDBEES', 'SILVERBEES'],
                'rationale': 'Non-correlated asset that preserves purchasing power during market corrections.'
            },
            {
                'category': 'Liquid STP Parking Fund',
                'percentage': 15,
                'color': '#10b981',
                'icon': 'fas fa-money-bill-transfer',
                'instruments': ['Overnight / Ultra Short Duration Debt'],
                'rationale': 'Holds dry powder to feed systematic transfers over 6 to 12 months.'
            }
        ]

        execution_steps = [
            {
                'step_num': 1,
                'title': 'Avoid 100% Day-One Market Dumps',
                'detail': f"{nifty_info}Do not deploy all {amount_str} in a single trading day to avoid catching local market tops.",
                'icon': 'fas fa-shield-halved'
            },
            {
                'step_num': 2,
                'title': 'Park in Liquid Fund & Run 6-Month STP',
                'detail': f"Park {amount_str} in a liquid fund and set up a weekly Systematic Transfer Plan (STP) across 24 weeks.",
                'icon': 'fas fa-clock-rotate-left'
            },
            {
                'step_num': 3,
                'title': 'Hold 20% Opportunistic Dip Reserve',
                'detail': 'Keep a 15% to 20% tranche ready to manually deploy if Nifty experiences a 4% to 7% correction.',
                'icon': 'fas fa-fire'
            },
            {
                'step_num': 4,
                'title': 'Harvest Profits with Foliux Rules',
                'detail': 'Once lots gain 20%+, systematically book profits back into liquid safety.',
                'icon': 'fas fa-hand-holding-dollar'
            }
        ]

        spoken_text = (
            f"Here is your FOLIUX institutional deployment plan for your {amount_str} lump sum. "
            "Crucial rule: do not invest the entire amount in a single day. "
            "Park the corpus in a liquid mutual fund and set up a 6-month Systematic Transfer Plan into equities. "
            "Target 45 percent in broad index ETFs like NIFTYBEES and ITBEES, 25 percent in top flexi-cap mutual funds, "
            "15 percent in Gold ETFs, and keep 15 percent as cash dry powder. "
            "If the market corrects 3 to 5 percent, deploy an extra tranche. "
            "This dollar cost averaging prevents the regret of buying at the top."
        )

        summary_text = (
            f"When managing a lump sum of **{amount_str}**, disciplined **Systematic Transfer (STP)** beats market timing. "
            "Staggering deployments over 6 months eliminates timing risk while keeping your capital working in liquid yields."
        )

    # -------------------------------------------------------------
    # 5. DEFAULT / MONTHLY SIP WEALTH CREATION (GENERAL)
    # -------------------------------------------------------------
    else:
        amt_disp = amount_str if amount_str else "₹10,000 / month"
        title = f"FOLIUX Wealth Engineering Allocation ({amt_disp})"
        
        allocations = [
            {
                'category': 'Core Index ETFs (Low Expense Ratio)',
                'percentage': 45,
                'color': '#2563eb',
                'icon': 'fas fa-chart-line',
                'instruments': ['NIFTYBEES (30%)', 'JUNIORBEES (15%)'],
                'rationale': 'Zero fund-manager risk; directly mirrors India’s top 100 enterprise growth.'
            },
            {
                'category': 'Flexi-Cap & Midcap Mutual Funds',
                'percentage': 30,
                'color': '#8b5cf6',
                'icon': 'fas fa-layer-group',
                'instruments': ['Parag Parikh Flexi Cap', 'Nippon India Growth Fund'],
                'rationale': 'Captures fast-growing mid-market leaders with disciplined quarterly rebalancing.'
            },
            {
                'category': 'Retirement Tax Compounding (NPS)',
                'percentage': 15,
                'color': '#f59e0b',
                'icon': 'fas fa-university',
                'instruments': ['NPS Tier-1 Scheme E/C'],
                'rationale': 'Long-term tax deduction under 80CCD(1B) with compulsory compounding.'
            },
            {
                'category': 'Gold & Liquid Reserve',
                'percentage': 10,
                'color': '#10b981',
                'icon': 'fas fa-coins',
                'instruments': ['GOLDBEES', 'Liquid Fund Buffer'],
                'rationale': 'Portfolio shock absorber during geopolitical and equity pullbacks.'
            }
        ]

        execution_steps = [
            {
                'step_num': 1,
                'title': 'Automate Your Recurring SIP',
                'detail': 'Set monthly auto-debits on your primary bank account for the 1st or 5th of every month.',
                'icon': 'fas fa-bolt'
            },
            {
                'step_num': 2,
                'title': 'Apply Foliux Pyramiding on Dips',
                'detail': 'When the Nifty 50 drops by 3% to 5%, buy an additional unit lot of NIFTYBEES or your core ETF.',
                'icon': 'fas fa-arrow-trend-down'
            },
            {
                'step_num': 3,
                'title': 'Enforce the 22% Profit Harvest Rule',
                'detail': 'When any individual purchase lot gains 20% to 22%, sell that lot and recycle the capital into underweight assets.',
                'icon': 'fas fa-scissors'
            },
            {
                'step_num': 4,
                'title': 'Use FIFO Accounting for Taxes',
                'detail': 'Foliux automatically applies First-In-First-Out accounting to maximize Long-Term Capital Gains exemption limits.',
                'icon': 'fas fa-calculator'
            }
        ]

        spoken_text = (
            f"Here is your FOLIUX investment strategy for {amt_disp}. "
            "To build disciplined, long-term wealth, divide your investment into four clear buckets: "
            "Allocate 45 percent to core index ETFs like NIFTYBEES and JUNIORBEES for steady foundation growth. "
            "Put 30 percent into proven Flexi-Cap mutual funds. "
            "Allocate 15 percent to the National Pension System for retirement compounding and tax savings, "
            "and 10 percent to Gold ETFs as a market hedge. "
            "Follow our two golden rules: buy additional units during 3 to 5 percent market dips, "
            "and harvest profits whenever a lot reaches a 22 percent profit. This keeps emotions out of your money."
        )

        summary_text = (
            f"With **{amt_disp}**, the proven strategy is a **Core-and-Satellite framework**: "
            "anchor 75% in broad index ETFs and mutual funds, while using NPS and Gold to protect and compound your net worth."
        )

    # Calculate monetary split if amount is available
    if amount and amount > 0:
        for item in allocations:
            item_val = round((item['percentage'] / 100.0) * amount)
            item['amount_formatted'] = f"₹{item_val:,.0f}" + (" / month" if is_sip else "")
    else:
        for item in allocations:
            item['amount_formatted'] = f"{item['percentage']}% Allocation"

    suggested_links = [
        {'title': 'Stock Guide', 'url': '/stock-guide/', 'icon': 'fas fa-chart-line', 'badge': 'Equity'},
        {'title': 'ETF Guide', 'url': '/etf-guide/', 'icon': 'fas fa-layer-group', 'badge': 'Passive'},
        {'title': 'Mutual Funds', 'url': '/mf-guide/', 'icon': 'fas fa-hand-holding-dollar', 'badge': 'SIP'},
        {'title': 'NPS Pension', 'url': '/nps-guide/', 'icon': 'fas fa-university', 'badge': 'Tax Saver'},
        {'title': 'Stock Screener', 'url': '/screener/', 'icon': 'fas fa-search', 'badge': 'Analysis'}
    ]

    return {
        'status': 'success',
        'query': query,
        'parsed_query': parsed,
        'title': title,
        'summary': summary_text,
        'spoken_text': spoken_text,
        'allocations': allocations,
        'execution_steps': execution_steps,
        'suggested_links': suggested_links,
        'disclaimer': (
            "Educational and rule-based decision support only. Foliux provides quantitative rules and allocation models. "
            "Investments in securities and mutual funds are subject to market risks. Please read all scheme documents carefully before investing."
        )
    }
