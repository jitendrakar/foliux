from django.urls import path
from . import views

app_name = 'npits'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('search/', views.search_view, name='search'),
    path('autocomplete/', views.autocomplete_view, name='autocomplete'),
    path('c/<slug:slug>/', views.category_detail_view, name='category_detail'),
    path('p/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('blog/', views.blog_list_view, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail_view, name='blog_detail'),
    path('sitemap.xml', views.sitemap_view, name='sitemap'),
    path('<slug:slug>/', views.seo_landing_view, name='seo_landing'),
]
