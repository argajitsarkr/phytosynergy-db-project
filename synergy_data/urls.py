# synergy_data/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Home page
    path('', views.home_page, name='home'),

    # Database search and download
    path('database/', views.database_search_page, name='database_search'),
    path('database/download/', views.download_data, name='download_data'),

    # About page
    path('about/', views.about_page, name='about'),

    # Data entry (login-protected)
    path('data-entry/', views.data_entry_view, name='data_entry'),
    path('data-entry/edit/<int:pk>/', views.edit_entry_view, name='edit_entry'),

    # Bulk CSV import (login-protected)
    path('bulk-import/', views.bulk_import_view, name='bulk_import'),
    path('bulk-import/template/', views.bulk_import_template, name='bulk_import_template'),

    # Analytics dashboard (public)
    path('analytics/', views.analytics_page, name='analytics'),

    # API endpoints
    path('api/v1/experiments/', views.api_experiments, name='api_experiments'),
    path('api/v1/statistics/', views.api_statistics, name='api_statistics'),
    path('api/docs/', views.api_docs, name='api_docs'),

    # Authentication
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='synergy_data/login.html'
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='home'
    ), name='logout'),
]
