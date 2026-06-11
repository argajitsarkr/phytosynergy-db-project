# phytosynergy_project/urls.py
from django.contrib import admin
from django.urls import path, include

from synergy_data import seo_views

urlpatterns = [
    # Any request for '/admin/' goes to the admin site.
    path('admin/', admin.site.urls),

    # SEO endpoints (must live at the site root).
    path('robots.txt', seo_views.robots_txt, name='robots_txt'),
    path('sitemap.xml', seo_views.sitemap_xml, name='sitemap_xml'),

    # Any other request (like the homepage) is handed off to our app's URL file.
    path('', include('synergy_data.urls')),
]