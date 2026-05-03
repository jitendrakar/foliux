from django.contrib import sitemaps
from django.urls import reverse

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
            'ipo',
            'strategy',
            'feedback',
        ]

    def location(self, item):
        return reverse(item)
