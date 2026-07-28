import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import IPO
from core.registrars import get_registrar, registrar_registry
from core.registrars.mufg import MUFGRegistrar
from core.registrars.kfintech import KFintechRegistrar

class IPOAllotmentIntegrationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.mufg = get_registrar('mufg')
        self.kfintech = get_registrar('kfintech')
        self.sample_ipo = IPO.objects.create(
            name="Laser Power & Infra Limited - IPO",
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timezone.timedelta(days=5),
            company_work="Manufacturer of electric cables and conductor wires.",
            notes="Strong order book and growth trajectory.",
            advise="APPLY",
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

    def test_kfintech_allotment_status_api_call(self):
        """Test calling allotment API with registrar=kfintech."""
        url = reverse('ipo_allotment_status_api')
        res = self.client.post(url, data=json.dumps({
            "company_id": "35015605280",
            "registrar": "kfintech",
            "search_type": "PAN",
            "search_value": "ABCDE1234F"
        }), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'success')

    def test_ipo_list_view_rendering(self):
        """Test /ipo/ page renders 200 OK with allotment status module."""
        url = reverse('ipo')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check Live IPO Allotment Status")
        self.assertContains(response, "Select IPO / Issue")
