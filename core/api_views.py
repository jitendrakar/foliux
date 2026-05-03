from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from core.utils import get_recommendations
from django.views.decorators.csrf import csrf_exempt
from .models import Instrument, Transaction, Portfolio, PnLStatement
from django.utils import timezone
from decimal import Decimal

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """
    API endpoint for mobile login.
    Supports username, email, or mobile number via the custom backend.
    """
    username = request.data.get('username') # Could be email or username
    password = request.data.get('password')
    
    if not username or not password:
        return Response({'status': 'error', 'message': 'Username and password are required'}, status=400)
    
    user = authenticate(username=username, password=password)
    
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'status': 'success',
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': getattr(user.profile, 'full_name', '') if hasattr(user, 'profile') else ''
            }
        })
    else:
        return Response({'status': 'error', 'message': 'Invalid credentials'}, status=401)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_portfolio(request):
    """
    API endpoint to retrieve the user's portfolio and dashboard summary.
    """
    try:
        recommendations, realized_profits, strategy_stocks = get_recommendations(request.user)
        
        # Calculate summary totals
        total_invested = sum(r.get('invested_amount', 0) for r in recommendations)
        total_current_value = sum(r.get('current_value', 0) for r in recommendations)
        total_unrealized_pnl = sum(r.get('unrealized_pnl', 0) for r in recommendations)
        total_realized_profit = sum(realized_profits.values())
        
        # Calculate P&L Percentage
        total_unrealized_pnl_percent = 0
        if total_invested > 0:
            total_unrealized_pnl_percent = (total_unrealized_pnl / total_invested) * 100

        return Response({
            'status': 'success',
            'summary': {
                'total_invested': float(total_invested),
                'total_current_value': float(total_current_value),
                'total_unrealized_pnl': float(total_unrealized_pnl),
                'total_unrealized_pnl_percent': float(total_unrealized_pnl_percent),
                'total_realized_profit': float(total_realized_profit),
            },
            'recommendations': recommendations
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'status': 'error', 'message': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_add_transaction(request):
    """
    API endpoint for adding a transaction from the mobile app.
    Integrates full business logic including portfolio updates and FIFO/Intraday for sells.
    """
    try:
        # Get data from request
        instrument_id = request.data.get('instrument_id')
        qty = int(request.data.get('quantity'))
        price = Decimal(str(request.data.get('price')))
        t_type = request.data.get('transaction_type') # 'BUY' or 'SELL'
        date_str = request.data.get('date')
        
        transaction_date = timezone.now().date()
        if date_str:
             try:
                 import pandas as pd
                 transaction_date = pd.to_datetime(date_str).date()
                 if transaction_date > timezone.now().date():
                     return Response({"status": "error", "message": "Date cannot be in the future."}, status=400)
             except:
                 pass

        instrument = Instrument.objects.get(id=instrument_id)
        
        if t_type == 'BUY':
            # Create Transaction record
            Transaction.objects.create(
                user=request.user,
                instrument=instrument,
                transaction_type='BUY',
                quantity=qty,
                remaining_quantity=qty,
                price=price,
                date=transaction_date
            )
            
            # Update/Create Portfolio record
            portfolio, created = Portfolio.objects.get_or_create(
                user=request.user, 
                instrument=instrument,
                defaults={'quantity': 0, 'avg_cost': Decimal('0'), 'ltp': price}
            )
            
            # Update Weighted Average Cost
            current_total_cost = Decimal(str(portfolio.quantity)) * portfolio.avg_cost
            new_total_cost = Decimal(str(qty)) * price
            total_quantity = portfolio.quantity + qty
            
            new_avg_cost = (current_total_cost + new_total_cost) / Decimal(str(total_quantity))
            
            portfolio.quantity = total_quantity
            portfolio.avg_cost = new_avg_cost
            if created or not portfolio.ltp or portfolio.ltp == 0:
                portfolio.ltp = price
            portfolio.save()
            
            return Response({"status": "success", "message": f"Successfully bought {qty} units of {instrument.symbol}"})

        elif t_type == 'SELL':
            # Verification of sufficiency
            portfolio = Portfolio.objects.filter(user=request.user, instrument=instrument).first()
            if not portfolio or qty > portfolio.quantity:
                 return Response({"status": "error", "message": f"Insufficient quantity. Current: {portfolio.quantity if portfolio else 0}"}, status=400)
            
            # 1. Intraday Logic
            intraday_buy = Transaction.objects.filter(
                user=request.user,
                instrument=instrument,
                transaction_type='BUY',
                date=transaction_date,
                quantity=qty,
                remaining_quantity=qty
            ).first()

            total_buy_value = Decimal('0')
            remaining_to_deduct = qty
            first_entry_date = None

            if intraday_buy:
                total_buy_value = Decimal(str(qty)) * intraday_buy.price
                first_entry_date = intraday_buy.date
                intraday_buy.remaining_quantity = 0
                intraday_buy.save()
                remaining_to_deduct = 0
            else:
                # 2. FIFO Logic
                buy_txs = Transaction.objects.filter(
                    user=request.user,
                    instrument=instrument,
                    transaction_type='BUY',
                    remaining_quantity__gt=0
                ).order_by('date', 'created_at')
                
                for tx in buy_txs:
                    if remaining_to_deduct <= 0:
                        break
                    
                    if first_entry_date is None:
                        first_entry_date = tx.date
                        
                    deduct = min(tx.remaining_quantity, remaining_to_deduct)
                    total_buy_value += Decimal(str(deduct)) * tx.price
                    tx.remaining_quantity -= deduct
                    tx.save()
                    remaining_to_deduct -= deduct
            
            sell_value = Decimal(str(qty)) * price
            profit = sell_value - total_buy_value
            
            # Record SELL Transaction
            Transaction.objects.create(
                user=request.user,
                instrument=instrument,
                transaction_type='SELL',
                quantity=qty,
                price=price,
                date=transaction_date
            )
            
            # Record in PnLStatement
            PnLStatement.objects.create(
                user=request.user,
                instrument=instrument,
                entry_date=first_entry_date,
                quantity=qty,
                buy_value=total_buy_value,
                sell_value=sell_value,
                realized_profit=profit,
                exit_date=transaction_date
            )
            
            # Update Portfolio
            portfolio.quantity -= qty
            if portfolio.quantity <= 0:
                portfolio.delete()
            else:
                # Recalculate average cost based on remaining lots
                remaining_lots = Transaction.objects.filter(
                    user=request.user,
                    instrument=instrument,
                    transaction_type='BUY',
                    remaining_quantity__gt=0
                )
                if remaining_lots.exists():
                    total_qty = sum(l.remaining_quantity for l in remaining_lots)
                    total_cost = sum(Decimal(str(l.remaining_quantity)) * l.price for l in remaining_lots)
                    portfolio.avg_cost = total_cost / Decimal(str(total_qty))
                portfolio.save()
            
            return Response({"status": "success", "message": f"Successfully sold {qty} units of {instrument.symbol}. Profit: {profit}"})

        else:
            return Response({"status": "error", "message": "Invalid transaction type"}, status=400)

    except Instrument.DoesNotExist:
        return Response({"status": "error", "message": "Instrument not found"}, status=404)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)
