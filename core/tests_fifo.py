from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import Instrument, Portfolio, Transaction, PnLStatement
from decimal import Decimal
from django.urls import reverse

class FIFOTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
        self.inst = Instrument.objects.create(symbol='TEST', name='Test Stock', is_verified=True)

    def test_fifo_profit_calculation(self):
        # 1. Buy 10 units @ 100
        response = self.client.post(reverse('buy_stock'), {'symbol': 'TEST', 'quantity': 10, 'price': '100'}, follow=True)
        self.assertEqual(response.status_code, 200)
        # 2. Buy 10 units @ 120
        response = self.client.post(reverse('buy_stock'), {'symbol': 'TEST', 'quantity': 10, 'price': '120'}, follow=True)
        self.assertEqual(response.status_code, 200)
        
        portfolio = Portfolio.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(portfolio.quantity, 20)
        self.assertEqual(portfolio.avg_cost, Decimal('110'))

        # 3. Sell 15 units @ 150
        response = self.client.post(reverse('sell_stock'), {'symbol': 'TEST', 'quantity': 15, 'price': '150'}, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Expected Profit calculation:
        # First 10 units: 10 * (150 - 100) = 500
        # Next 5 units: 5 * (150 - 120) = 150
        # Total Realized Profit: 650
        
        pnl = PnLStatement.objects.get(user=self.user, instrument=self.inst)
        self.assertEqual(pnl.realized_profit, Decimal('650'))
        
        # Remaining Portfolio
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.quantity, 5)
        # Average cost of remaining 5 units should be 120
        self.assertEqual(portfolio.avg_cost, Decimal('120'))
        
        # Remaining transactions
        remaining_tx = Transaction.objects.get(user=self.user, instrument=self.inst, remaining_quantity__gt=0)
        self.assertEqual(remaining_tx.remaining_quantity, 5)
        self.assertEqual(remaining_tx.price, Decimal('120'))

    def test_historical_price_analysis_in_lot_breakdown(self):
        # 1. Buy 10 units @ 100
        self.client.post(reverse('buy_stock'), {'symbol': 'TEST', 'quantity': 10, 'price': '100'}, follow=True)
        # 2. Buy 10 units @ 120
        self.client.post(reverse('buy_stock'), {'symbol': 'TEST', 'quantity': 10, 'price': '120'}, follow=True)
        # 3. Sell 15 units @ 150
        self.client.post(reverse('sell_stock'), {'symbol': 'TEST', 'quantity': 15, 'price': '150'}, follow=True)

        # 4. Access lot breakdown page
        response = self.client.get(reverse('lot_breakdown', args=[self.inst.id]))
        self.assertEqual(response.status_code, 200)

        ha = response.context['historical_analysis']
        # 1. Average Buy Price: across all 20 units bought = (10*100 + 10*120)/20 = 110.00
        self.assertEqual(ha['avg_buy_price'], Decimal('110.00'))
        self.assertEqual(ha['total_buy_qty'], 20)
        self.assertEqual(ha['buy_tx_count'], 2)
        self.assertEqual(ha['min_buy_price'], Decimal('100.00'))
        self.assertEqual(ha['max_buy_price'], Decimal('120.00'))

        # 2. Average Sell Price: across all 15 units sold = 150.00
        self.assertEqual(ha['avg_sell_price'], Decimal('150.00'))
        self.assertEqual(ha['total_sell_qty'], 15)
        self.assertEqual(ha['sell_tx_count'], 1)

        # 3. Buy Price Indicator: suggests buying at or below average buy price
        self.assertEqual(ha['buy_range_high'], Decimal('110.00'))
        self.assertIsNotNone(ha['buy_range_low'])
        self.assertIsNotNone(ha['buy_indicator_status'])

        # 4. Sell Price Indicator: suggests selling at or above average sell price
        self.assertEqual(ha['sell_range_low'], Decimal('150.00'))
        self.assertIsNotNone(ha['sell_indicator_status'])

        # Realized spread: 150 - 110 = 40
        self.assertEqual(ha['realized_spread'], Decimal('40.00'))

        # Check HTML content rendering
        content = response.content.decode('utf-8')
        self.assertIn("Historical Buy &amp; Sell Price Analysis", content)
        self.assertIn("Avg Buy Price", content)
        self.assertIn("Avg Sell Price", content)
        self.assertIn("Buy Price Indicator", content)
        self.assertIn("Sell Price Indicator", content)
        self.assertIn("110.00", content)
        self.assertIn("150.00", content)

    def test_historical_price_analysis_no_sells(self):
        # Buy 10 units @ 200
        self.client.post(reverse('buy_stock'), {'symbol': 'TEST', 'quantity': 10, 'price': '200'}, follow=True)

        response = self.client.get(reverse('lot_breakdown', args=[self.inst.id]))
        self.assertEqual(response.status_code, 200)

        ha = response.context['historical_analysis']
        self.assertEqual(ha['avg_buy_price'], Decimal('200.00'))
        self.assertIsNone(ha['avg_sell_price'])
        self.assertEqual(ha['total_sell_qty'], 0)
        # Sell indicator should suggest profit target price (200 * 1.22 = 244.00)
        self.assertIsNotNone(ha['target_sell_price'])
        self.assertEqual(ha['target_sell_price'], Decimal('244.00'))

        content = response.content.decode('utf-8')
        self.assertIn("No sales recorded", content)
        self.assertIn("244.00", content)
