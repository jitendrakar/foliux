"""
URL configuration for investment_advisory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap, BlogPostSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('salon/', include('salon.urls')),
    path('tailor/', include('tailor.urls')),
    path('screener/', include('screener.urls')),
    path('search-instruments/', core_views.search_instruments, name='search_instruments'),
    path('', include('core.urls')),
    # Custom password change view
    path('accounts/password_change/', core_views.CustomPasswordChangeView.as_view(), name='password_change'),
    # allauth handles /accounts/social/*, /accounts/login/, /accounts/logout/ etc.
    path('accounts/', include('allauth.urls')),
    # Fallback: Django built-in auth URLs (logout, password change)
    path('accounts/', include('django.contrib.auth.urls')),
]

from django.urls import re_path
from django.views.static import serve

from django.views.generic import TemplateView

urlpatterns += [
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]


