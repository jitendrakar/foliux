"""
URL configuration for restaurant project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Support admin panel with and without prefix
    path('restaurant/admin/', admin.site.urls),
    path('admin/', admin.site.urls),
    
    # Support app routes with and without prefix
    path('restaurant/', include('restaurant.urls')),
    path('', include('restaurant.urls')),
]

# Serve media and static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
