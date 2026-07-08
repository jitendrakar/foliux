from django.test import TestCase
from django.contrib.auth.models import User
from core.models import OtherAsset, FixedAsset
from core.views import get_fy_cashflow_details
from datetime import date
from decimal import Decimal

class CashflowIntegrationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_other_assets_rent_integration(self):
        # Create an other asset with monthly rent
        OtherAsset.objects.create(
            user=self.user,
            name="Rental Property",
            asset_type="Flat",
            purchase_date=date(2026, 4, 15),
            purchase_price=Decimal("5000000.00"),
            actual_market_value=Decimal("5000000.00"),
            monthly_rent=Decimal("15000.00")
        )
        # Call cashflow details for FY 2026-2027
        # Since purchase_date is 2026-04-15:
        # April 2026 monthly rent should be included (m_end = 2026-04-30 >= 2026-04-15)
        monthly_data, fy_totals = get_fy_cashflow_details(self.user, "2026-2027", current_date=date(2027, 3, 31))
        
        # April is index 0 of monthly_data (since FY starts in April)
        april_data = monthly_data[0]
        self.assertEqual(april_data['other_income'], Decimal("15000.00"))
        self.assertEqual(fy_totals['other_income'], Decimal("15000.00") * 12)

    def test_fd_interest_no_principal(self):
        # Create an FD with principal 100,000 and 6% interest rate
        FixedAsset.objects.create(
            user=self.user,
            instrument_name="Fixed Deposit 1",
            asset_type="FD",
            invested_amount="100000",
            interest_rate="6.0",
            investment_date=date(2026, 6, 15),
            maturity_date=date(2027, 6, 15)
        )
        monthly_data, fy_totals = get_fy_cashflow_details(self.user, "2026-2027", current_date=date(2026, 7, 31))
        
        # June 2026 is index 2 (April=0, May=1, June=2)
        june_data = monthly_data[2]
        # June should NOT include the principal 100,000 in interest income.
        self.assertLess(june_data['fd_interest'], Decimal("1000.00"))
        
        # July 2026 is index 3. It should include the monthly interest: 100,000 * 0.06 / 12 = 500
        july_data = monthly_data[3]
        self.assertAlmostEqual(july_data['fd_interest'], Decimal("500.00"), places=1)


class IdempotencyTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_duplicate_submission_blocked(self):
        # First POST with a unique idempotency key should succeed (redirects to other_assets_dashboard)
        response1 = self.client.post('/other-assets/add/', {
            'name': 'Gold ETF',
            'asset_type': 'Gold',
            'purchase_date': '2026-06-01',
            'purchase_price': '50000',
            'current_value': '52000',
            'idempotency_key': 'test-unique-key-123'
        })
        self.assertEqual(response1.status_code, 302)
        
        # Verify the asset was created
        self.assertEqual(OtherAsset.objects.filter(user=self.user, name='Gold ETF').count(), 1)

        # Repeating same request with same key should be blocked and redirected
        response2 = self.client.post('/other-assets/add/', {
            'name': 'Gold ETF',
            'asset_type': 'Gold',
            'purchase_date': '2026-06-01',
            'purchase_price': '50000',
            'current_value': '52000',
            'idempotency_key': 'test-unique-key-123'
        })
        self.assertEqual(response2.status_code, 302)
        
        # Verify no duplicate asset was created (count is still 1)
        self.assertEqual(OtherAsset.objects.filter(user=self.user, name='Gold ETF').count(), 1)


class BlogPostEmailNotificationTestCase(TestCase):
    def setUp(self):
        from core.models import BlogPost
        from django.core import mail
        self.BlogPost = BlogPost
        self.mail = mail
        self.author = User.objects.create_user(username='author', email='author@example.com', password='password')
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password')
        self.inactive_user = User.objects.create_user(username='inactive', email='inactive@example.com', password='password', is_active=False)

    def test_draft_does_not_send_email(self):
        # Create a draft blog post
        post = self.BlogPost.objects.create(
            title="Draft Post",
            slug="draft-post",
            content="This is a draft",
            author=self.author,
            status="draft"
        )
        self.assertEqual(len(self.mail.outbox), 0)
        self.assertFalse(post.email_sent)

    def test_publish_sends_email_once(self):
        # Create a draft post
        post = self.BlogPost.objects.create(
            title="Test Post",
            slug="test-post",
            content="Some content",
            author=self.author,
            status="draft"
        )
        self.assertEqual(len(self.mail.outbox), 0)
        
        # Publish it
        post.status = "published"
        post.save()
        
        # Wait for the background email thread to finish
        import threading
        for t in threading.enumerate():
            if t is not threading.current_thread() and t.name.startswith("Thread"):
                t.join(timeout=2)
                
        # Expect 3 emails (author, user1, user2)
        self.assertEqual(len(self.mail.outbox), 3)
        self.assertTrue(post.email_sent)
        
        # Edit the published post
        post.title = "Updated Test Post"
        post.save()
        
        for t in threading.enumerate():
            if t is not threading.current_thread() and t.name.startswith("Thread"):
                t.join(timeout=2)
                
        # Verify no additional emails were sent (count remains 3)
        self.assertEqual(len(self.mail.outbox), 3)

    def test_direct_publish_sends_email(self):
        # Create directly as published
        post = self.BlogPost.objects.create(
            title="Direct Post",
            slug="direct-post",
            content="Direct content",
            author=self.author,
            status="published"
        )
        
        import threading
        for t in threading.enumerate():
            if t is not threading.current_thread() and t.name.startswith("Thread"):
                t.join(timeout=2)
                
        self.assertEqual(len(self.mail.outbox), 3)
        self.assertTrue(post.email_sent)


class SavedCalculationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_ajax_login_api(self):
        self.client.logout()
        import json
        response = self.client.post('/calc/api/login/', json.dumps({
            'username': 'testuser',
            'password': 'password'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Invalid login
        response = self.client.post('/calc/api/login/', json.dumps({
            'username': 'testuser',
            'password': 'wrongpassword'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_save_calculation_api(self):
        import json
        payload = {
            'calc_type': 'sip',
            'calc_name': 'SIP Calculator',
            'name': 'My Retirement Fund',
            'input_values': {'monthly': 10000, 'rate': 12, 'tenure': 20},
            'calculated_results': {'corpus': 10000000}
        }
        response = self.client.post('/calc/api/save/', json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue('id' in data)

        calc_id = data['id']
        from core.models import SavedCalculation
        calc = SavedCalculation.objects.get(id=calc_id)
        self.assertEqual(calc.name, 'My Retirement Fund')
        self.assertEqual(calc.input_values['monthly'], 10000)

        # Update calculation under same ID
        payload['id'] = calc_id
        payload['name'] = 'My Retirement Fund - Updated'
        response = self.client.post('/calc/api/save/', json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        calc.refresh_from_db()
        self.assertEqual(calc.name, 'My Retirement Fund - Updated')

    def test_saved_calculations_list_api(self):
        from core.models import SavedCalculation
        SavedCalculation.objects.create(
            user=self.user,
            calc_type='sip',
            calc_name='SIP Calculator',
            name='First SIP',
            input_values={'monthly': 5000},
            calculated_results={'corpus': 500000}
        )
        SavedCalculation.objects.create(
            user=self.user,
            calc_type='emi',
            calc_name='Loan EMI Calculator',
            name='House Loan',
            input_values={'principal': 5000000},
            calculated_results={'emi': 45000}
        )

        response = self.client.get('/calc/api/list/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_count'], 2)

        # Search filter
        response = self.client.get('/calc/api/list/?q=House')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_count'], 1)
        self.assertEqual(data['data'][0]['name'], 'House Loan')

    def test_toggle_favorite_calculation_api(self):
        from core.models import SavedCalculation
        calc = SavedCalculation.objects.create(
            user=self.user,
            calc_type='sip',
            calc_name='SIP Calculator',
            name='My SIP',
            input_values={'monthly': 5000},
            calculated_results={'corpus': 500000}
        )
        self.assertFalse(calc.is_favorite)

        response = self.client.post(f'/calc/api/toggle-favorite/{calc.id}/')
        self.assertEqual(response.status_code, 200)
        calc.refresh_from_db()
        self.assertTrue(calc.is_favorite)

    def test_duplicate_calculation_api(self):
        from core.models import SavedCalculation
        calc = SavedCalculation.objects.create(
            user=self.user,
            calc_type='sip',
            calc_name='SIP Calculator',
            name='My SIP',
            input_values={'monthly': 5000},
            calculated_results={'corpus': 500000}
        )

        response = self.client.post(f'/calc/api/duplicate/{calc.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        new_id = data['id']

        self.assertEqual(SavedCalculation.objects.count(), 2)
        new_calc = SavedCalculation.objects.get(id=new_id)
        self.assertEqual(new_calc.name, 'My SIP (Copy)')

    def test_delete_calculation_api(self):
        from core.models import SavedCalculation
        calc = SavedCalculation.objects.create(
            user=self.user,
            calc_type='sip',
            calc_name='SIP Calculator',
            name='My SIP',
            input_values={'monthly': 5000},
            calculated_results={'corpus': 500000}
        )

        response = self.client.post(f'/calc/api/delete/{calc.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SavedCalculation.objects.count(), 0)


class DrDemoTestCase(TestCase):
    def test_dr_index_page(self):
        # Accessing /dr/ should return the doctor landing page with 200 OK
        response = self.client.get('/dr/')
        self.assertEqual(response.status_code, 200)
        # Verify it has some expected content from the clinic index page
        self.assertContains(response, "Dr. Inam's Clinic")

    def test_dr_redirect(self):
        # Accessing /dr without trailing slash should redirect to /dr/
        response = self.client.get('/dr')
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.url.endswith('/dr/'))

    def test_dr_static_file(self):
        # Accessing /dr/clinic1.webp should return 200 OK and be an image
        response = self.client.get('/dr/clinic1.webp')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'image/webp')

    def test_dr_directory_traversal_protection(self):
        # Attempting directory traversal should return 404 Not Found
        response = self.client.get('/dr/../manage.py')
        self.assertEqual(response.status_code, 404)

    def test_dr_nonexistent_file(self):
        # Accessing a nonexistent file should return 404 Not Found
        response = self.client.get('/dr/nonexistent_file.xyz')
        self.assertEqual(response.status_code, 404)


class IPOTestCase(TestCase):
    def test_ipo_cmp_property(self):
        from core.models import IPO, Instrument
        from datetime import date
        # Create an Instrument
        inst = Instrument.objects.create(
            name="Test Stock",
            symbol="TSTOCK",
            last_price=Decimal("123.45"),
            price_change=Decimal("2.30")
        )
        # Create an IPO with the symbol
        ipo = IPO.objects.create(
            name="Test IPO",
            symbol="TSTOCK",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 5),
            company_work="Does test operations",
            notes="Analysis notes"
        )
        self.assertEqual(ipo.cmp, Decimal("123.45"))
        self.assertEqual(ipo.price_change, Decimal("2.30"))
        
        # Test default/none properties when symbol doesn't exist
        ipo_no_sym = IPO.objects.create(
            name="Test IPO 2",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 5),
            company_work="Does other operations",
            notes="Analysis notes"
        )
        self.assertIsNone(ipo_no_sym.cmp)
        self.assertIsNone(ipo_no_sym.price_change)


class FinancialYearValidationTestCase(TestCase):
    def test_normalize_and_validate_fy(self):
        from core.models import normalize_and_validate_fy
        
        # Valid cases
        self.assertEqual(normalize_and_validate_fy("FY 2025-26"), "FY 2025-26")
        self.assertEqual(normalize_and_validate_fy("2025-26"), "FY 2025-26")
        self.assertEqual(normalize_and_validate_fy("2025-2026"), "FY 2025-26")
        self.assertEqual(normalize_and_validate_fy("FY 2025-2026"), "FY 2025-26")
        
        # Invalid cases
        with self.assertRaises(ValueError):
            normalize_and_validate_fy("FY 2025-2611")
        with self.assertRaises(ValueError):
            normalize_and_validate_fy("FY 2026-277")
        with self.assertRaises(ValueError):
            normalize_and_validate_fy("FY 2027-288")
        with self.assertRaises(ValueError):
            normalize_and_validate_fy("2025-27") # non-consecutive
            
    def test_model_save_normalization(self):
        from core.models import IncomeTaxProfile
        user = User.objects.create_user(username='fyuser', password='password')
        
        # Save profile with non-prefixed consecutive format
        profile = IncomeTaxProfile.objects.create(
            user=user,
            financial_year="2025-26",
            pan="ABCDE1234F",
            name="John Doe",
            dob="1990-01-01"
        )
        # Verify it normalized to 'FY 2025-26' on save
        self.assertEqual(profile.financial_year, "FY 2025-26")
        
        # Try to save with invalid format and check ValidationError
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            profile.financial_year = "FY 2025-2611"
            profile.save()


class AccountResetTestCase(TestCase):
    def test_reset_account_data_clears_ais_and_tax(self):
        from core.models import IncomeTaxProfile, IncomeTaxTds, UserTaxProfile, SavedCalculation, CashFlowEntry
        from core.views import reset_account_data
        from datetime import date
        
        user = User.objects.create_user(username='resetuser', password='password')
        
        # Create some AIS profile & TDS data
        IncomeTaxProfile.objects.create(
            user=user,
            financial_year="FY 2025-26",
            pan="ABCDE1234F",
            name="John Doe",
            dob="1990-01-01"
        )
        IncomeTaxTds.objects.create(
            user=user,
            financial_year="FY 2025-26",
            deductor_name="Mock Deductor",
            amount_paid=10000,
            tax_deducted=1000
        )
        UserTaxProfile.objects.create(
            user=user,
            financial_year="FY 2025-26",
            salary=500000
        )
        SavedCalculation.objects.create(
            user=user,
            calc_type="sip",
            calc_name="SIP Calculator",
            name="My SIP",
            input_values={},
            calculated_results={}
        )
        CashFlowEntry.objects.create(
            user=user,
            entry_type="INCOME",
            category="SALARY",
            amount=50000,
            date=date(2026, 4, 15)
        )
        
        # Verify they exist
        self.assertEqual(IncomeTaxProfile.objects.filter(user=user).count(), 1)
        self.assertEqual(IncomeTaxTds.objects.filter(user=user).count(), 1)
        self.assertEqual(UserTaxProfile.objects.filter(user=user).count(), 1)
        self.assertEqual(SavedCalculation.objects.filter(user=user).count(), 1)
        self.assertEqual(CashFlowEntry.objects.filter(user=user).count(), 1)
        
        # Perform reset
        reset_account_data(user)
        
        # Verify all are cleared
        self.assertEqual(IncomeTaxProfile.objects.filter(user=user).count(), 0)
        self.assertEqual(IncomeTaxTds.objects.filter(user=user).count(), 0)
        self.assertEqual(UserTaxProfile.objects.filter(user=user).count(), 0)
        self.assertEqual(SavedCalculation.objects.filter(user=user).count(), 0)
        self.assertEqual(CashFlowEntry.objects.filter(user=user).count(), 0)


class RamjaaTestCase(TestCase):
    def test_ramjaa_index(self):
        # Accessing the main index of ramjaa should return 200 OK
        response = self.client.get('/ramjaa/')
        self.assertEqual(response.status_code, 200)
        
    def test_ramjaa_static_file(self):
        # Accessing a static file like style.css should return 200 OK
        response = self.client.get('/ramjaa/style.css')
        self.assertEqual(response.status_code, 200)

    def test_ramjaa_nonexistent_file(self):
        # Accessing a nonexistent file should return 404
        response = self.client.get('/ramjaa/nonexistent.xyz')
        self.assertEqual(response.status_code, 404)







