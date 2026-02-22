# synergy_data/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('database/', views.database_search_page, name='database_search'),
    path('database/download/', views.download_data, name='download_data'),
    path('stats/', views.stats_page, name='stats'),
    path('about/', views.about_page, name='about'),
    path('health/', views.health_check, name='health_check'),
]
