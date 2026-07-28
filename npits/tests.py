from django.test import TestCase, Client
from django.urls import reverse
from npits.models import (
    NPITSConfig, NPITSCategory, NPITSProduct, 
    NPITSAffiliateLink, NPITSArticle, NPITSSeoLanding
)
from npits.affiliates import AmazonAffiliateProvider, get_affiliate_provider

class NPITSAppTests(TestCase):

    def setUp(self):
        self.client = Client()
        
        # Ensure config
        NPITSConfig.objects.get_or_create(
            key="AMAZON_ASSOCIATE_ID",
            defaults={"value": "npits09-21"}
        )

        self.category = NPITSCategory.objects.create(
            name="SSD (256GB, 512GB, 1TB, 2TB)",
            slug="ssd",
            icon_class="fas fa-memory",
            order=1
        )

        self.product = NPITSProduct.objects.create(
            title="Crucial BX500 512GB SATA SSD",
            slug="crucial-bx500-512gb-sata-ssd",
            brand="Crucial",
            category=self.category,
            asin="B07YD579WM",
            image_url="https://example.com/ssd.jpg",
            price=3299.00,
            original_price=4200.00,
            rating=4.6,
            review_count=1200,
            capacity="512GB",
            amazon_url="https://www.amazon.in/dp/B07YD579WM"
        )

        self.seo_landing = NPITSSeoLanding.objects.create(
            slug="best-512gb-ssd",
            title="Best 512GB SSD",
            h1_title="Best 512GB SSD in India",
            meta_title="Best 512GB SSD Guide",
            target_category=self.category,
            capacity_filter="512GB"
        )

        self.article = NPITSArticle.objects.create(
            title="Best SSD for Laptop",
            slug="best-ssd-for-laptop",
            summary="Guide to upgrading your laptop with an SSD.",
            content="Detailed content about SSD upgrades.",
            category=self.category
        )

    def test_amazon_associate_id_link_generation(self):
        """Test that Amazon URLs automatically contain tag=npits09-21."""
        tracked_url = self.product.get_tracked_amazon_url()
        self.assertIn("tag=npits09-21", tracked_url)
        self.assertTrue(tracked_url.startswith("https://www.amazon.in"))

    def test_affiliate_provider_engine(self):
        """Test modular affiliate provider engine."""
        provider = get_affiliate_provider("amazon")
        self.assertIsInstance(provider, AmazonAffiliateProvider)
        url = provider.build_affiliate_url("https://www.amazon.in/dp/123456", "npits09-21")
        self.assertIn("tag=npits09-21", url)

    def test_home_view(self):
        """Test NPITS home view rendering."""
        url = reverse('npits:home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FOLIUX NPITS")
        self.assertContains(response, "Crucial BX500 512GB SATA SSD")

    def test_category_detail_view(self):
        """Test category detail page rendering."""
        url = reverse('npits:category_detail', kwargs={'slug': 'ssd'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crucial BX500 512GB SATA SSD")

    def test_product_detail_view(self):
        """Test product detail page rendering and Schema.org markup."""
        url = reverse('npits:product_detail', kwargs={'slug': 'crucial-bx500-512gb-sata-ssd'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crucial BX500 512GB SATA SSD")
        self.assertContains(response, "tag=npits09-21")
        self.assertContains(response, '"@type": "Product"')

    def test_seo_landing_view(self):
        """Test custom SEO landing page view."""
        url = reverse('npits:seo_landing', kwargs={'slug': 'best-512gb-ssd'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Best 512GB SSD in India")

    def test_search_view(self):
        """Test multi-field search."""
        url = reverse('npits:search') + "?q=Crucial"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crucial BX500 512GB SATA SSD")

    def test_sitemap_view(self):
        """Test dynamic XML sitemap generation."""
        url = reverse('npits:sitemap')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], "application/xml")
        self.assertContains(response, "<urlset")
