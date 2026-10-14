import json
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import IPO
from core.chittorgarh import parse_chittorgarh_dates
from core.ipo_sync import auto_sync_foliux_ipos
from core.registrars import get_registrar, registrar_registry
from core.registrars.mufg import MUFGRegistrar
from core.registrars.kfintech import KFintechRegistrar

class IPOAllotmentIntegrationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.mufg = get_registrar('mufg')
        self.kfintech = get_registrar('kfintech')
        
        # Patch external registrar network calls
        self.patcher_mufg = patch('core.registrars.mufg.MUFGRegistrar.get_active_ipos', return_value=[{'id': '11913', 'name': 'Laser Power & Infra Limited', 'registrar': 'mufg'}])
        self.patcher_kfin = patch('core.registrars.kfintech.KFintechRegistrar.get_active_ipos', return_value=[])
        self.mock_mufg_ipos = self.patcher_mufg.start()
        self.mock_kfin_ipos = self.patcher_kfin.start()
        self.addCleanup(self.patcher_mufg.stop)
        self.addCleanup(self.patcher_kfin.stop)

        self.sample_ipo = IPO.objects.create(
            name="Laser Power & Infra Limited - IPO",
            symbol="",
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timezone.timedelta(days=5),
            company_work="Manufacturer of electric cables and conductor wires.",
            notes="Strong order book and growth trajectory.",
            advise="APPLY",
            subscription_times=Decimal('4.50'),
            gmp_percent=Decimal('35.00'),
            gmp_amount=Decimal('50.00'),
            registrar_slug="mufg",
            registrar_company_id="11913",
            is_synced_from_registrar=True,
            is_active=True
        )

    def test_mufg_registrar_token_encryption(self):
        """Test MUFG AES token encryption matches PKCS7 padded base64 standard."""
        self.assertIsNotNone(self.mufg)
        self.assertEqual(self.mufg.slug, "mufg")
        token_raw = "123456789"
        encrypted = self.mufg._encrypt_token(token_raw)
        self.assertTrue(isinstance(encrypted, str))
        self.assertTrue(len(encrypted) > 0)

    def test_kfintech_registrar_instance(self):
        """Test KFintech registrar instance properties."""
        self.assertIsNotNone(self.kfintech)
        self.assertEqual(self.kfintech.slug, "kfintech")
        self.assertEqual(self.kfintech.name, "KFintech")

    def test_registrar_registry(self):
        """Test RegistrarRegistry registers and fetches registrars correctly."""
        reg_mufg = registrar_registry.get_registrar("mufg")
        self.assertIsNotNone(reg_mufg)
        self.assertIsInstance(reg_mufg, MUFGRegistrar)

        reg_kfintech = registrar_registry.get_registrar("kfintech")
        self.assertIsNotNone(reg_kfintech)
        self.assertIsInstance(reg_kfintech, KFintechRegistrar)

        all_regs = registrar_registry.get_all_registrars()
        self.assertTrue(any(r['slug'] == 'mufg' for r in all_regs))
        self.assertTrue(any(r['slug'] == 'kfintech' for r in all_regs))

    def test_ipo_companies_api(self):
        """Test GET /api/ipo/companies/ API endpoint."""
        url = reverse('ipo_companies_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue('companies' in data)

    def test_ipo_allotment_status_api_validation(self):
        """Test validation in POST /api/ipo/allotment-status/ endpoint."""
        url = reverse('ipo_allotment_status_api')
        
        # Test missing company_id
        res1 = self.client.post(url, data=json.dumps({
            "search_type": "PAN",
            "search_value": "ABCDE1234F"
        }), content_type="application/json")
        self.assertEqual(res1.status_code, 400)
        self.assertEqual(res1.json()['status'], 'error')

        # Test missing search_value
        res2 = self.client.post(url, data=json.dumps({
            "company_id": "11913",
            "search_type": "PAN",
            "search_value": ""
        }), content_type="application/json")
        self.assertEqual(res2.status_code, 400)

        # Test invalid registrar
        res3 = self.client.post(url, data=json.dumps({
            "company_id": "11913",
            "registrar": "non_existent_registrar",
            "search_type": "PAN",
            "search_value": "ABCDE1234F"
        }), content_type="application/json")
        self.assertEqual(res3.status_code, 400)

    @patch('core.registrars.kfintech.requests.post')
    def test_kfintech_allotment_status_api_call(self, mock_post):
        """Test calling allotment API with registrar=kfintech."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = [{'STATUS': 'ALLOTTED', 'SHARES': 100}]
        url = reverse('ipo_allotment_status_api')
        res = self.client.post(url, data=json.dumps({
            "company_id": "35015605280",
            "registrar": "kfintech",
            "search_type": "PAN",
            "search_value": "ABCDE1234F"
        }), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'success')

    @patch('core.views._auto_update_ipos')
    def test_ipo_list_view_rendering(self, mock_auto_update):
        """Test /ipo/ page renders 200 OK with subscription, GMP, and advise badges."""
        mock_auto_update.return_value = [{'id': '11913', 'name': 'Laser Power & Infra Limited', 'registrar': 'mufg'}]
        url = reverse('ipo')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check Live IPO Allotment Status")
        self.assertContains(response, "Subscription")
        self.assertContains(response, "GMP")
        self.assertContains(response, "Laser Power")

    def test_chittorgarh_date_parsing(self):
        """Test parsing various Chittorgarh date string formats."""
        s1, e1 = parse_chittorgarh_dates("11 to 16 Sep, 2026")
        self.assertEqual(s1, timezone.datetime(2026, 9, 11).date())
        self.assertEqual(e1, timezone.datetime(2026, 9, 16).date())

        s2, e2 = parse_chittorgarh_dates("Friday, September 11, 2026")
        self.assertEqual(s2, timezone.datetime(2026, 9, 11).date())
        self.assertEqual(e2, timezone.datetime(2026, 9, 11).date())

    @patch('core.ipo_sync.fetch_chittorgarh_ipos')
    def test_auto_sync_foliux_ipos_start_date_today(self, mock_fetch):
        """Test IPO starting TODAY is auto-added with advise=WAITING."""
        today = timezone.localdate()
        mock_fetch.return_value = [{
            'name': 'Future Mobility India IPO',
            'symbol': 'MOBILITY',
            'start_date': today,
            'end_date': today + timezone.timedelta(days=3),
            'company_work': 'EV component manufacturer.',
            'notes': 'High growth potential.',
            'registrar_slug': 'kfintech',
            'subscription_times': Decimal('1.20'),
            'gmp_percent': Decimal('15.00'),
            'gmp_amount': Decimal('20.00'),
        }]

        stats = auto_sync_foliux_ipos()
        self.assertEqual(stats['added'], 1)
        
        created = IPO.objects.get(name='Future Mobility India')
        self.assertEqual(created.advise, 'WAITING')
        self.assertEqual(created.start_date, today)
        self.assertTrue(created.is_active)

    @patch('core.ipo_sync.fetch_chittorgarh_ipos')
    def test_auto_sync_foliux_ipos_skip_future_and_closed(self, mock_fetch):
        """Test upcoming IPO is added for tracking and old closed IPO (>30d) is skipped."""
        today = timezone.localdate()
        mock_fetch.return_value = [
            {
                'name': 'Upcoming Next Month Tech IPO',
                'start_date': today + timezone.timedelta(days=10),
                'end_date': today + timezone.timedelta(days=13),
                'company_work': 'AI software provider.',
            },
            {
                'name': 'Very Old Closed Heritage IPO',
                'start_date': today - timezone.timedelta(days=45),
                'end_date': today - timezone.timedelta(days=40),
                'company_work': 'Textile manufacturer.',
            }
        ]

        stats = auto_sync_foliux_ipos()
        self.assertEqual(stats['added'], 1)
        self.assertTrue(IPO.objects.filter(name='Upcoming Next Month Tech').exists())
        self.assertFalse(IPO.objects.filter(name='Very Old Closed Heritage').exists())

    @patch('core.ipo_sync.fetch_chittorgarh_ipos')
    def test_auto_sync_foliux_ipos_2nd_day_apply_logic(self, mock_fetch):
        """Test on 2nd day, advise becomes APPLY only when subscription >= 3x AND GMP > 30%."""
        today = timezone.localdate()
        yesterday = today - timezone.timedelta(days=1)  # Today is Day 2!

        existing = IPO.objects.create(
            name="SuperTech Solar Solutions Limited",
            start_date=yesterday,
            end_date=yesterday + timezone.timedelta(days=3),
            company_work="Solar panels manufacturer.",
            notes="Solar boom",
            advise="WAITING",
            subscription_times=Decimal('1.00'),
            gmp_percent=Decimal('10.00'),
            is_active=True
        )

        mock_fetch.return_value = [{
            'name': 'SuperTech Solar Solutions Limited',
            'start_date': yesterday,
            'end_date': yesterday + timezone.timedelta(days=3),
            'subscription_times': Decimal('4.20'),  # >= 3x
            'gmp_percent': Decimal('45.00'),        # > 30%
            'gmp_amount': Decimal('60.00'),
        }]

        stats = auto_sync_foliux_ipos()
        self.assertEqual(stats['updated'], 1)

        existing.refresh_from_db()
        self.assertEqual(existing.advise, 'APPLY')

    @patch('core.ipo_sync.fetch_chittorgarh_ipos')
    def test_auto_sync_foliux_ipos_2nd_day_waiting_fallback(self, mock_fetch):
        """Test on 2nd day, advise stays WAITING if either subscription < 3x OR GMP <= 30%."""
        today = timezone.localdate()
        yesterday = today - timezone.timedelta(days=1)  # Today is Day 2

        existing = IPO.objects.create(
            name="Moderate Retailers Limited",
            start_date=yesterday,
            end_date=yesterday + timezone.timedelta(days=3),
            company_work="Retail chain.",
            notes="Retail chain review.",
            advise="WAITING",
            subscription_times=Decimal('5.00'),  # >= 3x
            gmp_percent=Decimal('20.00'),        # <= 30% (Fails condition)
            is_active=True
        )

        mock_fetch.return_value = [{
            'name': 'Moderate Retailers Limited',
            'start_date': yesterday,
            'end_date': yesterday + timezone.timedelta(days=3),
            'subscription_times': Decimal('5.00'),
            'gmp_percent': Decimal('20.00'),
        }]

        auto_sync_foliux_ipos()
        existing.refresh_from_db()
        self.assertEqual(existing.advise, 'WAITING')

    def test_scrape_chittorgarh_subscription_parsing(self):
        """Test Chittorgarh subscription multiplier table extraction."""
        from core.chittorgarh import scrape_chittorgarh_subscription
        sample_html = """
        <html><body>
        <table>
            <tr><th>Category</th><th>Shares Offered</th><th>Amt (Cr)</th></tr>
            <tr><td>Total</td><td>2,62,84,500</td><td>712.31</td></tr>
        </table>
        <table>
            <tr><th>Investor Category</th><th>Subscription (times)</th></tr>
            <tr><td>Qualified Institutional</td><td>1.43x</td></tr>
            <tr><td>Non Institutional</td><td>36.96x</td></tr>
            <tr><td>Retail Individual</td><td>9.43x</td></tr>
            <tr><td>Total Subscription</td><td>13.02x</td></tr>
        </table>
        </body></html>
        """
        with patch('core.chittorgarh.fetch_url_soup') as mock_soup:
            from bs4 import BeautifulSoup
            mock_soup.return_value = BeautifulSoup(sample_html, 'html.parser')
            sub = scrape_chittorgarh_subscription('https://www.chittorgarh.com/ipo_subscription/test-ipo/123/')
            self.assertEqual(sub, Decimal('13.02'))

    def test_scrape_investorgain_gmp_detail_parsing(self):
        """Test Investorgain individual review page scraper for GMP and subscription."""
        from core.investorgain import scrape_investorgain_gmp_detail
        sample_html = """
        <html><body>
        <h1>Fusion CX IPO GMP Today & History</h1>
        <table>
            <tr><th>GMP Date</th><th>GMP</th><th>Est. Listing Priceon upper price-₹289.00</th><th>Est. Profit</th></tr>
            <tr><td>14-Oct 15:02Sub: 0.32xO</td><td>₹33(11.42%)</td><td>₹322</td><td>₹1,683</td></tr>
        </table>
        </body></html>
        """
        with patch('urllib.request.urlopen') as mock_urlopen:
            import io
            mock_resp = io.BytesIO(sample_html.encode('utf-8'))
            mock_resp.status = 200
            mock_resp.geturl = lambda: 'https://www.investorgain.com/gmp/fusion-cx-ipo-gmp/1792/'
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            detail = scrape_investorgain_gmp_detail('https://www.investorgain.com/gmp/fusion-cx-ipo-gmp/1792/')
            self.assertIsNotNone(detail)
            self.assertEqual(detail['name'], 'Fusion CX')
            self.assertEqual(detail['gmp_amount'], Decimal('33'))
            self.assertEqual(detail['gmp_percent'], Decimal('11.42'))
            self.assertEqual(detail['price'], Decimal('289.00'))
            self.assertEqual(detail['subscription_times'], Decimal('0.32'))

    def test_investorgain_matching_and_enrichment(self):
        """Test matching between database IPOs and Investorgain records."""
        from core.investorgain import match_investorgain_record
        records = {
            'fusion cx': {'name': 'Fusion CX', 'gmp_amount': Decimal('33'), 'gmp_percent': Decimal('11.42'), 'url': 'https://www.investorgain.com/gmp/fusion-cx-ipo/1792/', 'slug': 'fusion-cx-ipo'},
            'zetwerk': {'name': 'Zetwerk', 'gmp_amount': Decimal('18'), 'gmp_percent': Decimal('11.92'), 'url': 'https://www.investorgain.com/gmp/zetwerk-ipo/2279/', 'slug': 'zetwerk-ipo'},
        }

        m1 = match_investorgain_record('Fusion CX', records)
        self.assertIsNotNone(m1)
        self.assertEqual(m1['name'], 'Fusion CX')

        m2 = match_investorgain_record('Zetwerk Manufacturing Business Limited IPO', records)
        self.assertIsNotNone(m2)
        self.assertEqual(m2['name'], 'Zetwerk')

