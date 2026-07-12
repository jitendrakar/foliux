from django.urls import path
from . import views

app_name = 'screener'

urlpatterns = [
    path('', views.screener_home, name='screener_home'),
    path('api/suggest/', views.screener_suggest, name='screener_suggest'),
    path('<str:symbol>/', views.company_detail, name='company_detail'),
]
