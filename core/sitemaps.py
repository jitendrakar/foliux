from django.contrib import sitemaps
from django.urls import reverse
from .models import BlogPost

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'daily'
    protocol = 'https'

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
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(sitemaps.Sitemap):
    changefreq = 'weekly'
    priority = 0.8
    protocol = 'https'

    def items(self):
        return BlogPost.objects.filter(status='published').order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at
