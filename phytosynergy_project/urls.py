# phytosynergy_project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Any request for '/admin/' goes to the admin site.
    path('admin/', admin.site.urls),
    
    # Any other request (like the homepage) is handed off to our app's URL file.
    path('', include('synergy_data.urls')), 
]