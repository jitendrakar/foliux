from django.urls import path
from . import views

app_name = 'salon'

urlpatterns = [
    # Public Pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('pricing/', views.pricing, name='pricing'),
    path('gallery/', views.gallery, name='gallery'),
    path('team/', views.team, name='team'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('contact/', views.contact, name='contact'),
    path('book/', views.book_appointment, name='book_appointment'),
    path('offers/', views.offers, name='offers'),
    
    # Customer Authentication & Profile
    path('login/', views.salon_login, name='login'),
    path('register/', views.salon_register, name='register'),
    path('logout/', views.salon_logout, name='logout'),
    path('profile/', views.salon_profile, name='profile'),
    
    # Custom Admin Dashboard
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    path('dashboard/appointments/', views.dashboard_appointments, name='dashboard_appointments'),
    path('dashboard/appointments/<int:pk>/update/', views.dashboard_appointment_update, name='dashboard_appointment_update'),
    
    # Dashboard CRUD for Services
    path('dashboard/services/', views.dashboard_services, name='dashboard_services'),
    path('dashboard/services/add/', views.dashboard_service_add, name='dashboard_service_add'),
    path('dashboard/services/<int:pk>/edit/', views.dashboard_service_edit, name='dashboard_service_edit'),
    path('dashboard/services/<int:pk>/delete/', views.dashboard_service_delete, name='dashboard_service_delete'),
    
    # Dashboard CRUD for Stylists
    path('dashboard/stylists/', views.dashboard_stylists, name='dashboard_stylists'),
    path('dashboard/stylists/add/', views.dashboard_stylist_add, name='dashboard_stylist_add'),
    path('dashboard/stylists/<int:pk>/edit/', views.dashboard_stylist_edit, name='dashboard_stylist_edit'),
    path('dashboard/stylists/<int:pk>/delete/', views.dashboard_stylist_delete, name='dashboard_stylist_delete'),

    # Dashboard CRUD for Gallery
    path('dashboard/gallery/', views.dashboard_gallery, name='dashboard_gallery'),
    path('dashboard/gallery/add/', views.dashboard_gallery_add, name='dashboard_gallery_add'),
    path('dashboard/gallery/<int:pk>/delete/', views.dashboard_gallery_delete, name='dashboard_gallery_delete'),
    
    # Dashboard CRUD for Testimonials
    path('dashboard/testimonials/', views.dashboard_testimonials, name='dashboard_testimonials'),
    path('dashboard/testimonials/add/', views.dashboard_testimonial_add, name='dashboard_testimonial_add'),
    path('dashboard/testimonials/<int:pk>/edit/', views.dashboard_testimonial_edit, name='dashboard_testimonial_edit'),
    path('dashboard/testimonials/<int:pk>/delete/', views.dashboard_testimonial_delete, name='dashboard_testimonial_delete'),

    # Dashboard CRUD for Offers
    path('dashboard/offers/', views.dashboard_offers, name='dashboard_offers'),
    path('dashboard/offers/add/', views.dashboard_offer_add, name='dashboard_offer_add'),
    path('dashboard/offers/<int:pk>/edit/', views.dashboard_offer_edit, name='dashboard_offer_edit'),
    path('dashboard/offers/<int:pk>/delete/', views.dashboard_offer_delete, name='dashboard_offer_delete'),

    # Dashboard CRUD for Blogs
    path('dashboard/blogs/', views.dashboard_blogs, name='dashboard_blogs'),
    path('dashboard/blogs/add/', views.dashboard_blog_add, name='dashboard_blog_add'),
    path('dashboard/blogs/<int:pk>/edit/', views.dashboard_blog_edit, name='dashboard_blog_edit'),
    path('dashboard/blogs/<int:pk>/delete/', views.dashboard_blog_delete, name='dashboard_blog_delete'),

    # Dashboard Customers List
    path('dashboard/customers/', views.dashboard_customers, name='dashboard_customers'),

    # Dashboard Settings
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
]
