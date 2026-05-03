from .utils import get_recommendations, get_target_user

def signal_info(request):
    """
    Context processor to provide buy/sell signal counts to all templates.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        from .models import MFPortfolio, CoinPortfolio, NPSPortfolio
        from decimal import Decimal
        
        target_user, is_family_view, is_consolidated = get_target_user(request)
        recommendations, _, _ = get_recommendations(target_user)
        
        # 1. Stocks & ETFs signals
        stock_buy = sum(1 for r in recommendations if r.get('action') == 'BUY')
        stock_reduce = sum(1 for r in recommendations if r.get('action') == 'REDUCE')
        stock_sell = sum(1 for r in recommendations if r.get('action') == 'SELL')
        stock_total = stock_buy + stock_reduce + stock_sell
        
        # 2. Mutual Funds signals
        mf_buy = 0
        mf_sell = 0
        mf_reduce = 0
        mf_limit = target_user.profile.mf_investment_limit
        mf_profit_target = float(target_user.profile.mf_profit_expectation)
        mf_holdings = MFPortfolio.objects.filter(user=target_user)
        for h in mf_holdings:
            # Suppress SELL if Realized Profit > Current Investment
            if h.pnl_percentage >= mf_profit_target and h.realized_profit <= h.invested_amount:
                mf_sell += 1
            
            target = mf_limit + h.realized_profit
            if h.invested_amount < target:
                mf_buy += 1
            elif h.invested_amount > target + Decimal('3000'):
                mf_reduce += 1
        mf_total = mf_buy + mf_sell + mf_reduce
                    
        # 3. Coin signals
        coin_buy = 0
        coin_sell = 0
        coin_reduce = 0
        coin_limit = target_user.profile.coin_investment_limit
        coin_profit_target = float(target_user.profile.coin_profit_expectation)
        coin_holdings = CoinPortfolio.objects.filter(user=target_user)
        for h in coin_holdings:
            # Suppress SELL if Realized Profit > Current Investment
            if h.pnl_percentage >= coin_profit_target and h.realized_profit <= h.invested_amount:
                coin_sell += 1
            
            target = coin_limit + h.realized_profit
            if h.invested_amount < target:
                coin_buy += 1
            elif h.invested_amount > target + Decimal('3000'):
                coin_reduce += 1
        coin_total = coin_buy + coin_sell + coin_reduce

        # 4. NPS signals (Wait 22% rule for NPS too)
        from django.db.models import F
        nps_sell = NPSPortfolio.objects.filter(user=target_user, fund__nav__gte=F('avg_nav') * Decimal('1.22')).count()
        # simplified nps check for now
        nps_total = nps_sell
        
        total_actions = stock_total + mf_total + coin_total + nps_total
        
        # Filter action_count based on current page
        url_name = request.resolver_match.url_name if request.resolver_match else ''
        display_count = total_actions # Default for Portfolio and other pages
        
        if url_name == 'mf_dashboard':
            display_count = mf_total
        elif url_name == 'coin_dashboard':
            display_count = coin_total
        elif url_name == 'dashboard':
            display_count = stock_total
        elif url_name == 'nps_dashboard':
            display_count = nps_total

        return {
            'total_signal_count': total_actions,
            'action_count': display_count,
            'stock_alert_count': stock_total,
            'mf_alert_count': mf_total,
            'coin_alert_count': coin_total,
            'nps_alert_count': nps_total,
            # Legacy fields for backward compatibility if used in templates
            'sell_count': stock_sell,
            'buy_count': stock_buy,
            'reduce_count': stock_reduce,
            'mf_buy_count': mf_buy,
            'mf_redemption_count': mf_sell,
            'coin_buy_count': coin_buy,
            'coin_sell_count': coin_sell,
        }
    except Exception as e:
        # Avoid crashing the entire site if recommendation logic fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in signal_info context processor: {e}")
        return {
            'total_signal_count': 0,
            'action_count': 0,
            'sell_count': 0,
            'buy_count': 0,
            'reduce_count': 0,
            'mf_buy_count': 0,
            'mf_redemption_count': 0,
            'coin_buy_count': 0,
            'coin_sell_count': 0,
            'has_sell_signal': False,
        }

def family_context(request):
    """
    Globally provides information about whether the current view is for a family member.
    """
    if not request.user.is_authenticated:
        return {}
    
    from .models import FamilyLink
    target_user, is_family_view, is_consolidated = get_target_user(request)
    
    return {
        'target_user': target_user,
        'is_family_view': is_family_view,
        'is_consolidated': is_consolidated,
        'linked_family': FamilyLink.objects.filter(user=request.user, is_verified=True).order_by('family_user__username')
    }

def ipo_info(request):
    """
    Context processor to provide the count of open IPOs to all templates.
    """
    from .models import IPO
    from django.utils import timezone
    today = timezone.now().date()
    # Count IPOs that are currently open AND have an "Apply" recommendation
    active_ipo_count = IPO.objects.filter(start_date__lte=today, end_date__gte=today, advise='APPLY').count()
    return {
        'active_ipo_count': active_ipo_count
    }
