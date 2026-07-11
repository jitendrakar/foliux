from django.test import TestCase, Client
from django.urls import reverse
from django.db import connections
from django.utils import timezone
from datetime import date, time

from salon.models import SalonUser, SalonCategory, SalonService, SalonStylist, SalonAppointment, SalonSetting

class SalonDatabaseRouterTest(TestCase):
    databases = {'default', 'salon'}
    """
    Test that the database router correctly routes reads, writes,
    and migrations for the salon app to the salon database.
    """
    def test_salon_models_routed_to_salon_db(self):
        # Verify the 'salon' database connection is configured
        self.assertIn('salon', connections)
        
        # Test routing for reads and writes
        from django.db import router
        user = SalonUser(name="Test User", email="test@test.com", mobile="9999999999", role="customer")
        
        # Check router selection
        db_read = router.db_for_read(SalonUser)
        db_write = router.db_for_write(SalonUser)
        
        self.assertEqual(db_read, 'salon')
        self.assertEqual(db_write, 'salon')


class SalonPublicViewsTest(TestCase):
    databases = {'default', 'salon'}
    """
    Test standard public views load successfully (HTTP 200).
    """
    def setUp(self):
        # Create a category, service, stylist, and settings for template rendering
        self.category = SalonCategory.objects.using('salon').create(category_name="Hair", status=True)
        self.service = SalonService.objects.using('salon').create(
            category=self.category,
            service_name="Test Hair Cut",
            price=299,
            duration=30,
            description="Nice trim",
            status=True
        )
        self.stylist = SalonStylist.objects.using('salon').create(
            name="Ramesh Kumar",
            designation="Master Stylist",
            experience="5 Years",
            description="Good designer",
            status=True
        )
        self.settings = SalonSetting.objects.using('salon').create(
            salon_name="SalonX Test",
            address="Test address",
            phone="9871808718",
            email="test@salonx.com",
            whatsapp="9871808718",
            opening_hours="9am - 9pm",
            google_map="https://maps.google.com"
        )
        self.client = Client()

    def test_home_view(self):
        response = self.client.get(reverse('salon:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Hair Cut")

    def test_about_view(self):
        response = self.client.get(reverse('salon:about'))
        self.assertEqual(response.status_code, 200)

    def test_services_view(self):
        response = self.client.get(reverse('salon:services'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Hair Cut")

    def test_pricing_view(self):
        response = self.client.get(reverse('salon:pricing'))
        self.assertEqual(response.status_code, 200)

    def test_team_view(self):
        response = self.client.get(reverse('salon:team'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ramesh Kumar")

    def test_contact_view(self):
        response = self.client.get(reverse('salon:contact'))
        self.assertEqual(response.status_code, 200)


class SalonBookingTest(TestCase):
    databases = {'default', 'salon'}
    """
    Test booking forms and appointment creation.
    """
    def setUp(self):
        self.category = SalonCategory.objects.using('salon').create(category_name="Hair", status=True)
        self.service = SalonService.objects.using('salon').create(
            category=self.category,
            service_name="Test Hair Cut",
            price=299,
            duration=30,
            description="Nice trim",
            status=True
        )
        self.stylist = SalonStylist.objects.using('salon').create(
            name="Ramesh Kumar",
            designation="Master Stylist",
            experience="5 Years",
            description="Good designer",
            status=True
        )
        self.client = Client()

    def test_booking_submission(self):
        booking_data = {
            'customer_name': 'Aarav Nair',
            'mobile': '9876543210',
            'email': 'aarav.nair@gmail.com',
            'gender': 'Male',
            'service': self.service.id,
            'stylist': self.stylist.id,
            'appointment_date': date.today().strftime('%Y-%m-%d'),
            'appointment_time': '14:30',
            'message': 'Looking forward to it.'
        }
        
        response = self.client.post(reverse('salon:book_appointment'), booking_data)
        
        # Should redirect back or render success
        self.assertEqual(response.status_code, 302)
        
        # Verify stored record in 'salon' database
        appt = SalonAppointment.objects.using('salon').filter(customer_name='Aarav Nair').first()
        self.assertIsNotNone(appt)
        self.assertEqual(appt.service.id, self.service.id)
        self.assertEqual(appt.stylist.id, self.stylist.id)


class SalonSessionAuthTest(TestCase):
    databases = {'default', 'salon'}
    """
    Test custom session authentication login, logout, and access restrictions.
    """
    def setUp(self):
        self.user = SalonUser.objects.using('salon').create(
            name="Test Customer",
            email="cust@test.com",
            mobile="9898989898",
            role="customer"
        )
        self.user.set_password("mypassword")
        self.user.save(using='salon')
        
        self.admin = SalonUser.objects.using('salon').create(
            name="Test Admin",
            email="admin@test.com",
            mobile="9797979797",
            role="admin"
        )
        self.admin.set_password("adminpassword")
        self.admin.save(using='salon')
        
        self.client = Client()

    def test_customer_login_success(self):
        # Submit login form
        response = self.client.post(reverse('salon:login'), {
            'email': 'cust@test.com',
            'password': 'mypassword'
        })
        self.assertEqual(response.status_code, 302)  # redirects to profile
        
        # Verify session variables are set
        session = self.client.session
        self.assertEqual(session.get('salon_user_id'), self.user.id)
        self.assertEqual(session.get('salon_user_role'), 'customer')

    def test_dashboard_requires_admin(self):
        # Access dashboard as anonymous user
        response = self.client.get(reverse('salon:dashboard_home'))
        self.assertEqual(response.status_code, 302)  # redirects to login
        
        # Access as regular customer user
        self.client.post(reverse('salon:login'), {
            'email': 'cust@test.com',
            'password': 'mypassword'
        })
        response = self.client.get(reverse('salon:dashboard_home'))
        self.assertEqual(response.status_code, 302)  # redirects to home because role is not admin
