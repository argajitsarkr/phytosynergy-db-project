# synergy_data/urls.py
from django.urls import path
from . import views

# This file maps specific URLs to their final destination (a view function).
urlpatterns = [
    # The root path '' maps to the home_page view.
    path('', views.home_page, name='home'),
    
    # The '/database/' path maps to the search page view.
    path('database/', views.database_search_page, name='database_search'),
    
    # The '/about/' path maps to the about page view.
    path('about/', views.about_page, name='about'),
    
    # The '/database/download/' path maps to the download feature.
    path('database/download/', views.download_data, name='download_data'),
]