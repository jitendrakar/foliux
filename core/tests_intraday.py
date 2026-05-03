from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from core.models import Instrument, Portfolio, Transaction, PnLStatement
from core.views import sell_stock
from decimal import Decimal
from django.utils import timezone
import datetime
from django.contrib.messages.storage.base import BaseStorage

class MockMessageStorage(BaseStorage):
    def __init__(self, request, *args, **kwargs):
        self._queued_messages = []
        super().__init__(request, *args, **kwargs)
    def _get(self, *args, **kwargs):
        return self._queued_messages, True
    def _store(self, messages, *args, **kwargs):
        self._queued_messages.extend(messages)
        return []

class IntradayTradeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.factory = RequestFactory()
        self.inst = Instrument.objects.create(symbol='TEST', name='Test Stock', is_verified=True)
        # Set brokerage to 0 for logic tests
        from core.models import Profile
        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.equity_brokerage_pct = Decimal('0')
        profile.intraday_brokerage_pct = Decimal('0')
        profile.equity_fixed_charge = Decimal('0')
        profile.intraday_fixed_charge = Decimal('0')
        profile.save()

    def _post_sell(self, data):
        request = self.factory.post('/portfolio/sell/', data)
        request.user = self.user
        setattr(request, '_messages', MockMessageStorage(request))
        return sell_stock(request)

    def test_standard_fifo(self):
        """Standard FIFO: Buy Day 1, Buy Day 2, Sell Day 3. Should use Day 1 buy."""
        day1 = timezone.now().date() - datetime.timedelta(days=2)
        day2 = timezone.now().date() - datetime.timedelta(days=1)
        day3 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2)
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=20, avg_cost=Decimal('110'), ltp=Decimal('120'))

        self._post_sell({'symbol': 'TEST', 'quantity': '10', 'price': '150', 'exit_date': day3.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('500')) # (150-100)*10
        
        remaining_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', remaining_quantity__gt=0)
        self.assertEqual(remaining_tx.date, day2)

    def test_intraday_match(self):
        """Intraday Match: Buy Day 1, Buy Day 2, Sell Day 2 (same volume as Buy 2). Should use Day 2 buy."""
        day1 = timezone.now().date() - datetime.timedelta(days=1)
        day2 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2)
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=20, avg_cost=Decimal('110'), ltp=Decimal('120'))

        self._post_sell({'symbol': 'TEST', 'quantity': '10', 'price': '150', 'exit_date': day2.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('300')) # (150-120)*10
        
        remaining_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', remaining_quantity__gt=0)
        self.assertEqual(remaining_tx.date, day1)

    def test_volume_mismatch_prioritize_intraday(self):
        """Volume Mismatch: Buy Day 1 (10). Buy Day 2 (10). Sell Day 2 (5). Should prioritize Day 2 (Intraday)."""
        day1 = timezone.now().date() - datetime.timedelta(days=1)
        day2 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2)
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=20, avg_cost=Decimal('110'), ltp=Decimal('120'))

        self._post_sell({'symbol': 'TEST', 'quantity': '5', 'price': '150', 'exit_date': day2.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        # Expected: Sell 5 against Day 2 buy (120). (150-120)*5 = 150
        self.assertEqual(pnl.realized_profit, Decimal('150'))
        
        day2_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day2)
        self.assertEqual(day2_tx.remaining_quantity, 5)
        
        day1_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day1)
        self.assertEqual(day1_tx.remaining_quantity, 10)

    def test_multiple_same_day_buys_fifo_within_day(self):
        """Multiple same-day buys: Should use them FIFO within the same day."""
        day1 = timezone.now().date() - datetime.timedelta(days=1)
        day2 = timezone.now().date()

        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('100'), date=day1)
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=10, remaining_quantity=10, price=Decimal('120'), date=day2) # Buy A
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=20, remaining_quantity=20, price=Decimal('130'), date=day2) # Buy B
        
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=40, avg_cost=Decimal('120'), ltp=Decimal('130'))

        # Sell 15 on Day 2. Should consume all 10 from Buy A and 5 from Buy B.
        self._post_sell({'symbol': 'TEST', 'quantity': '15', 'price': '150', 'exit_date': day2.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        # (150-120)*10 + (150-130)*5 = 300 + 100 = 400
        self.assertEqual(pnl.realized_profit, Decimal('400'))
        
        self.assertEqual(Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day1).remaining_quantity, 10)
        self.assertEqual(Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day2, quantity=10).remaining_quantity, 0)
        self.assertEqual(Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day2, quantity=20).remaining_quantity, 15)

    def test_complex_intraday_fifo_mix(self):
        """
        User Scenario: Already have 60 (Older). Buy 50 (Today). Sell 60 (Today).
        Result: 50 should be matched as intraday, 10 should be matched from older lot (FIFO).
        """
        day_older = timezone.now().date() - datetime.timedelta(days=7)
        day_today = timezone.now().date()

        # 1. Existing holding of 60 units
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=60, remaining_quantity=60, price=Decimal('100'), date=day_older)
        
        # 2. Buy 50 units today
        Transaction.objects.create(user=self.user, instrument=self.inst, transaction_type='BUY', quantity=50, remaining_quantity=50, price=Decimal('110'), date=day_today)
        
        Portfolio.objects.create(user=self.user, instrument=self.inst, quantity=110, avg_cost=Decimal('104.54'), ltp=Decimal('110'))

        # 3. Sell 60 units today
        self._post_sell({'symbol': 'TEST', 'quantity': '60', 'price': '150', 'exit_date': day_today.isoformat()})
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        # Expected Buy Value: (50 * 110) [Intraday] + (10 * 100) [FIFO] = 5500 + 1000 = 6500
        # Sell Value: 60 * 150 = 9000
        # Profit: 9000 - 6500 = 2500
        self.assertEqual(pnl.realized_profit, Decimal('2500'))
        
        # Check remaining quantities
        day_today_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day_today)
        self.assertEqual(day_today_tx.remaining_quantity, 0) # Fully consumed
        
        day_older_tx = Transaction.objects.get(user=self.user, instrument=self.inst, transaction_type='BUY', date=day_older)
        self.assertEqual(day_older_tx.remaining_quantity, 50) # 60 - 10 = 50


