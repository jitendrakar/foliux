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
            current_value=Decimal("5000000.00"),
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


