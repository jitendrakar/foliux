from django.test import TestCase, Client
from django.urls import reverse
from restaurant.models import Category, MenuItem, Reservation, ContactMessage
import datetime

class RestaurantViewsTestCase(TestCase):
    databases = {'default', 'restaurant'}

    def setUp(self):
        self.client = Client()
        # Set up a category
        self.category = Category.objects.create(
            name="Appetizers",
            description="Start your meal with our appetizers."
        )
        # Set up a menu item
        self.menu_item = MenuItem.objects.create(
            category=self.category,
            name="Garlic Bread",
            description="Bread toasted with garlic butter.",
            price=6.50,
            is_veg=True,
            is_available=True
        )

    def test_pages_respond_200(self):
        # List of pages to test
        pages = ['home', 'about', 'menu', 'categories', 'specials', 'gallery', 'reservation', 'testimonials', 'blog_list', 'contact']
        for page in pages:
            response = self.client.get(reverse(page))
            self.assertEqual(response.status_code, 200, f"Page {page} failed to respond with 200.")

    def test_menu_search_and_filtering(self):
        # Test search query
        response = self.client.get(reverse('menu'), {'q': 'Garlic'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Garlic Bread")

        # Test filter by category
        response = self.client.get(reverse('menu'), {'category': self.category.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Garlic Bread")

    def test_reservation_creation(self):
        # Test valid reservation POST
        reservation_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '1234567890',
            'date': (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
            'time': '19:00:00',
            'guests': 4,
            'special_request': 'Window table if possible.'
        }
        response = self.client.post(reverse('reservation'), data=reservation_data)
        self.assertRedirects(response, reverse('reservation'))
        
        # Verify it exists in database
        self.assertEqual(Reservation.objects.count(), 1)
        res = Reservation.objects.first()
        self.assertEqual(res.name, 'John Doe')
        self.assertEqual(res.guests, 4)

    def test_reservation_past_date_invalid(self):
        # Test past date reservation (should fail validation)
        reservation_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '1234567890',
            'date': '2020-01-01', # Past date
            'time': '19:00:00',
            'guests': 4,
            'special_request': ''
        }
        response = self.client.post(reverse('reservation'), data=reservation_data)
        # Should not redirect, should render the form again with errors
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_contact_form_submission(self):
        # Test contact message submission
        contact_data = {
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'phone': '0987654321',
            'subject': 'Feedback',
            'message': 'Love the food!'
        }
        response = self.client.post(reverse('contact'), data=contact_data)
        self.assertRedirects(response, reverse('contact'))
        
        # Verify it exists in database
        self.assertEqual(ContactMessage.objects.count(), 1)
        msg = ContactMessage.objects.first()
        self.assertEqual(msg.name, 'Jane Smith')
        self.assertEqual(msg.subject, 'Feedback')
