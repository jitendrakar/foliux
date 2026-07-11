from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from tailor.models import (
    TailorUser, TailorService, TailorMeasurement, TailorOrder, 
    TailorAppointment, TailorSetting
)

class TailorDatabaseRouterTest(TestCase):
    databases = {'default', 'tailor'}
    """
    Test that the database router correctly routes reads, writes,
    and migrations for the tailor app to the tailor database.
    """
    def setUp(self):
        # Create a setting object
        self.setting = TailorSetting.objects.create(
            brand_name="Test Brand",
            address="Test Address",
            phone="123456",
            email="test@test.com",
            whatsapp="123456",
            google_map="https://map.com"
        )
        self.service = TailorService.objects.create(
            category="Men's Tailoring",
            service_name="Test Shirt",
            price=500.00,
            icon="fa-shirt",
            description="Test description",
            status=True
        )

    def test_routing_read_write(self):
        # Verify writing to tailor goes to the tailor db
        setting_db = TailorSetting.objects.db_manager('tailor').first()
        self.assertEqual(setting_db.brand_name, "Test Brand")
        
        service_db = TailorService.objects.db_manager('tailor').first()
        self.assertEqual(service_db.service_name, "Test Shirt")


class TailorPublicViewsTest(TestCase):
    databases = {'default', 'tailor'}
    """
    Test standard public views load successfully (HTTP 200).
    """
    def setUp(self):
        self.client = Client()
        self.setting = TailorSetting.objects.create(
            brand_name="Test Brand",
            address="Test Address",
            phone="123456",
            email="test@test.com",
            whatsapp="123456",
            google_map="https://map.com"
        )
        self.service = TailorService.objects.create(
            category="Men's Tailoring",
            service_name="Test Shirt",
            price=500.00,
            icon="fa-shirt",
            description="Test description",
            status=True
        )

    def test_public_pages_status(self):
        pages = ['tailor:home', 'tailor:about', 'tailor:services', 'tailor:gallery', 'tailor:pricing', 'tailor:contact', 'tailor:book_appointment', 'tailor:track_order', 'tailor:login', 'tailor:register']
        for page in pages:
            url = reverse(page)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Page {page} failed to load.")


class TailorMeasurementTest(TestCase):
    databases = {'default', 'tailor'}
    """
    Test measurement submissions and recording sizes.
    """
    def setUp(self):
        self.client = Client()
        self.setting = TailorSetting.objects.create(
            brand_name="Test Brand",
            address="Test Address",
            phone="123456",
            email="test@test.com",
            whatsapp="123456",
            google_map="https://map.com"
        )

    def test_measurement_request_submission(self):
        url = reverse('tailor:measurement_request')
        post_data = {
            'guest_name': 'Tester Sizing',
            'guest_mobile': '9999999999',
            'guest_email': 'testsize@test.com',
            'height': '180 cm',
            'chest': '40 in',
            'waist': '34 in',
            'notes': 'Loose shoulders requested.'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302) # Redirects to home on success
        
        # Verify user and measurements created
        user = TailorUser.objects.filter(mobile='9999999999').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, 'Tester Sizing')
        
        measurement = TailorMeasurement.objects.filter(customer=user).first()
        self.assertIsNotNone(measurement)
        self.assertEqual(measurement.chest, '40 in')
        self.assertEqual(measurement.waist, '34 in')


class TailorSessionAuthTest(TestCase):
    databases = {'default', 'tailor'}
    """
    Test custom session authentication login, logout, and access restrictions.
    """
    def setUp(self):
        self.client = Client()
        self.setting = TailorSetting.objects.create(
            brand_name="Test Brand",
            address="Test Address",
            phone="123456",
            email="test@test.com",
            whatsapp="123456",
            google_map="https://map.com"
        )
        self.customer = TailorUser(
            name="Test Customer",
            mobile="9800000000",
            email="cust@test.com",
            role="customer"
        )
        self.customer.set_password("cust123")
        self.customer.save()
        
        self.admin = TailorUser(
            name="Test Admin",
            mobile="9811111111",
            email="admin@test.com",
            role="admin"
        )
        self.admin.set_password("admin123")
        self.admin.save()

    def test_access_protection_customer_profile(self):
        url = reverse('tailor:profile')
        # Try accessing profile without logging in
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redirects to login
        self.assertIn('/tailor/login/', response.url)

    def test_access_protection_admin_dashboard(self):
        url = reverse('tailor:dashboard_home')
        # Try accessing dashboard without logging in
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # Log in as Customer
        session = self.client.session
        session['tailor_user_id'] = self.customer.id
        session['tailor_user_role'] = self.customer.role
        session.save()
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redirects to home because not an admin

    def test_admin_dashboard_success(self):
        url = reverse('tailor:dashboard_home')
        # Log in as Admin
        session = self.client.session
        session['tailor_user_id'] = self.admin.id
        session['tailor_user_role'] = self.admin.role
        session.save()
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200) # Dashboard successfully loads
