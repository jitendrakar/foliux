from django.urls import path
from . import views

app_name = 'screener'

urlpatterns = [
    path('', views.screener_home, name='screener_home'),
    path('search/', views.nl_search_view, name='nl_search'),
    path('management-credibility/', views.management_credibility_dashboard, name='management_credibility'),
    path('doc-viewer/<int:doc_id>/', views.serve_local_document, name='serve_local_document'),
    path('api/suggest/', views.screener_suggest, name='screener_suggest'),
    path('api/nl-search/', views.nl_search_api, name='nl_search_api'),
    path('api/nl-suggest/', views.nl_suggest_api, name='nl_suggest_api'),
    path('<str:symbol>/', views.company_detail, name='company_detail'),
]
