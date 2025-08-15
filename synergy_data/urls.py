# phytosynergy_project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # This is the correct line for your homepage and other app pages
    path('', include('synergy_data.urls')), 
]