# synergy_data/urls.py
from django.contrib import admin
from django.urls import path, include
from synergy_data import views as synergy_views # Import views for direct access

urlpatterns = [
    # TEMPORARY: For debugging, we are making the failsafe health_check our homepage.
    path('', synergy_views.health_check, name='health_check'),

    # The other URLs are still here but won't be used by the root path for now.
    path('admin/', admin.site.urls),
    path('app/', include('synergy_data.urls')), 
]