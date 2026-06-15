from django.contrib import sitemaps
from django.urls import reverse
from .models import BlogPost

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'daily'
    protocol = 'https'

    def get_domain(self, site=None):
        return 'foliux.com'

    def items(self):
        return [
            'landing',
            'about_project',
            'mf_guide',
            'etf_guide',
            'nps_guide',
            'stock_guide',
            'education_hub',
            'stock_news',
            'ipo',
            'strategy',
            'feedback',
            'wealth_calculators',
            'login',
            'register',
            'forgot_password',
            'cashflow_dashboard',
            '/education/share-market-taxation-in-india-stcg-ltcg-intraday-fo-tax-rules-explained/',
            '/education/why-the-ideal-asset-allocation-could-be-33-real-estate-33-equity-and-33-fixed-assets/',
        ]

    def location(self, item):
        if item.startswith('/'):
            return item
        return reverse(item)


class BlogPostSitemap(sitemaps.Sitemap):
    changefreq = 'weekly'
    priority = 0.8
    protocol = 'https'

    def get_domain(self, site=None):
        return 'foliux.com'

    def items(self):
        return BlogPost.objects.filter(status='published').order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at
