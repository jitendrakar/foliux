from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('menu/', views.menu, name='menu'),
    path('categories/', views.categories, name='categories'),
    path('specials/', views.specials, name='specials'),
    path('gallery/', views.gallery, name='gallery'),
    path('reservation/', views.reservation, name='reservation'),
    path('testimonials/', views.testimonials, name='testimonials'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('contact/', views.contact, name='contact'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
]
