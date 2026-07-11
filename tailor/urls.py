from django.urls import path
from . import views

app_name = 'tailor'

urlpatterns = [
    # Public Pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('gallery/', views.gallery, name='gallery'),
    path('pricing/', views.pricing, name='pricing'),
    path('contact/', views.contact, name='contact'),
    path('book/', views.book_appointment, name='book_appointment'),
    path('measurement-request/', views.measurement_request, name='measurement_request'),
    path('track/', views.track_order, name='track_order'),
    
    # Customer Authentication & Profile
    path('login/', views.tailor_login, name='login'),
    path('register/', views.tailor_register, name='register'),
    path('logout/', views.tailor_logout, name='logout'),
    path('profile/', views.tailor_profile, name='profile'),
    
    # Admin Dashboard
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    
    # Customer Management
    path('dashboard/customers/', views.dashboard_customers, name='dashboard_customers'),
    path('dashboard/customers/<int:pk>/edit/', views.dashboard_customer_edit, name='dashboard_customer_edit'),
    path('dashboard/customers/<int:pk>/delete/', views.dashboard_customer_delete, name='dashboard_customer_delete'),
    
    # Measurement Management
    path('dashboard/measurements/', views.dashboard_measurements, name='dashboard_measurements'),
    path('dashboard/measurements/add/', views.dashboard_measurement_add, name='dashboard_measurement_add'),
    path('dashboard/measurements/<int:pk>/edit/', views.dashboard_measurement_edit, name='dashboard_measurement_edit'),
    
    # Order Management
    path('dashboard/orders/', views.dashboard_orders, name='dashboard_orders'),
    path('dashboard/orders/add/', views.dashboard_order_add, name='dashboard_order_add'),
    path('dashboard/orders/<int:pk>/edit/', views.dashboard_order_edit, name='dashboard_order_edit'),
    path('dashboard/orders/<int:pk>/delete/', views.dashboard_order_delete, name='dashboard_order_delete'),
    path('dashboard/orders/<int:pk>/invoice/', views.dashboard_order_invoice, name='dashboard_order_invoice'),
    
    # Appointment Management
    path('dashboard/appointments/', views.dashboard_appointments, name='dashboard_appointments'),
    path('dashboard/appointments/<int:pk>/update/', views.dashboard_appointment_update, name='dashboard_appointment_update'),
    
    # Payment Management
    path('dashboard/payments/', views.dashboard_payments, name='dashboard_payments'),
    path('dashboard/payments/add/', views.dashboard_payment_add, name='dashboard_payment_add'),
    
    # Gallery Management
    path('dashboard/gallery/', views.dashboard_gallery, name='dashboard_gallery'),
    path('dashboard/gallery/add/', views.dashboard_gallery_add, name='dashboard_gallery_add'),
    path('dashboard/gallery/<int:pk>/delete/', views.dashboard_gallery_delete, name='dashboard_gallery_delete'),
    
    # Pricing/Services Management
    path('dashboard/pricing/', views.dashboard_pricing, name='dashboard_pricing'),
    path('dashboard/pricing/add/', views.dashboard_pricing_add, name='dashboard_pricing_add'),
    path('dashboard/pricing/<int:pk>/edit/', views.dashboard_pricing_edit, name='dashboard_pricing_edit'),
    path('dashboard/pricing/<int:pk>/delete/', views.dashboard_pricing_delete, name='dashboard_pricing_delete'),
    
    # Reviews
    path('dashboard/reviews/', views.dashboard_reviews, name='dashboard_reviews'),
    path('dashboard/reviews/<int:pk>/approve/', views.dashboard_review_approve, name='dashboard_review_approve'),
    path('dashboard/reviews/<int:pk>/delete/', views.dashboard_review_delete, name='dashboard_review_delete'),
    
    # Offer Management
    path('dashboard/offers/', views.dashboard_offers, name='dashboard_offers'),
    path('dashboard/offers/add/', views.dashboard_offer_add, name='dashboard_offer_add'),
    path('dashboard/offers/<int:pk>/edit/', views.dashboard_offer_edit, name='dashboard_offer_edit'),
    path('dashboard/offers/<int:pk>/delete/', views.dashboard_offer_delete, name='dashboard_offer_delete'),
    
    # Reports
    path('dashboard/reports/', views.dashboard_reports, name='dashboard_reports'),
    
    # Settings
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
]
