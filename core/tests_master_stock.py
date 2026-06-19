from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Instrument, Portfolio

class MasterStockDatabaseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')
        
        # Create verified instruments
        self.inst1 = Instrument.objects.create(name='Reliance Industries', symbol='RELIANCE', is_verified=True)
        self.inst2 = Instrument.objects.create(name='Tata Consultancy Services', symbol='TCS', is_verified=True)
        self.inst3 = Instrument.objects.create(name='Unverified Stock', symbol='WRONG', is_verified=False)

    def test_search_instruments_api(self):
        # Search by name
        response = self.client.get(reverse('search_instruments'), {'q': 'Reli'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['symbol'], 'RELIANCE')

        # Search by symbol
        response = self.client.get(reverse('search_instruments'), {'q': 'TCS'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Tata Consultancy Services')

        # Unverified should not appear
        response = self.client.get(reverse('search_instruments'), {'q': 'WRONG'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)

    def test_add_portfolio_validation(self):
        from django.utils import timezone
        today_str = timezone.localdate().isoformat()
        # Valid verified stock
        response = self.client.post(reverse('add_portfolio_item'), {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-company_name': 'Reliance Industries',
            'form-0-symbol': 'RELIANCE',
            'form-0-quantity': '10',
            'form-0-avg_cost': '2500',
            'form-0-date': today_str,
            'form-0-trade_type': 'NORMAL',
        })
        self.assertEqual(response.status_code, 302) # Redirect to dashboard
        self.assertTrue(Portfolio.objects.filter(instrument__symbol='RELIANCE').exists())

        # Invalid unverified stock
        response = self.client.post(reverse('add_portfolio_item'), {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-company_name': 'Wrong Stock',
            'form-0-symbol': 'WRONG',
            'form-0-quantity': '10',
            'form-0-avg_cost': '100',
            'form-0-date': today_str,
            'form-0-trade_type': 'NORMAL',
        })
        self.assertEqual(response.status_code, 200) # Form redisplays
        # Check that it didn't create a portfolio item
        self.assertFalse(Portfolio.objects.filter(instrument__symbol='WRONG').exists())

    def test_report_missing_instrument(self):
        from core.models import MissingInstrumentRequest
        from django.core import mail
        import json
        import time
        
        # Test posting valid name (default type is Stock/ETF)
        response = self.client.post(
            reverse('report_missing_instrument'),
            json.dumps({'name': 'ABC Global ETF'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['message'], 'Stock/ETF name has been sent to the admin for review.')
        
        # Check that request was saved in database
        self.assertEqual(MissingInstrumentRequest.objects.filter(searched_name='[Stock/ETF] ABC Global ETF').count(), 1)
        req = MissingInstrumentRequest.objects.get(searched_name='[Stock/ETF] ABC Global ETF')
        self.assertEqual(req.user, self.user)
        self.assertEqual(req.status, 'pending')
        
        # Test posting with a specific type (e.g. Mutual Fund)
        response2 = self.client.post(
            reverse('report_missing_instrument'),
            json.dumps({'name': 'Axis Bluechip Fund', 'type': 'Mutual Fund'}),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(MissingInstrumentRequest.objects.filter(searched_name='[Mutual Fund] Axis Bluechip Fund').count(), 1)

        # Wait a split second for the background thread to send the email
        time.sleep(0.5)
        
        self.assertEqual(len(mail.outbox), 2)
        subjects = [m.subject for m in mail.outbox]
        self.assertIn('[FOLIUX] Missing Stock/ETF Report: ABC Global ETF', subjects)
        self.assertIn('[FOLIUX] Missing Mutual Fund Report: Axis Bluechip Fund', subjects)
        for m in mail.outbox:
            self.assertEqual(m.to, ['jitendra.kar@gmail.com'])
