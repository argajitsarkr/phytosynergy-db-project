# synergy_data/seo_views.py
"""Lightweight SEO endpoints: robots.txt and an XML sitemap.

Hand-rolled (no django.contrib.sitemaps / sites framework) because the public
site has a small, fixed set of indexable pages and no per-record detail URLs,
so a dependency-free view keeps things simple and avoids an extra migration.
"""
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse

# (url name, priority, change frequency) for each public, indexable page.
SITEMAP_PAGES = [
    ('home', '1.0', 'weekly'),
    ('database_search', '0.9', 'daily'),
    ('analytics', '0.8', 'weekly'),
    ('about', '0.7', 'monthly'),
    ('download_data', '0.7', 'weekly'),
    ('api_docs', '0.6', 'monthly'),
]


def _abs(path):
    """Absolute URL on the canonical domain for a root-relative path."""
    return settings.SITE_URL + path


def robots_txt(request):
    """Allow crawling of public pages; keep private/admin/API-JSON out of the
    index; advertise the sitemap."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /data-entry/",
        "Disallow: /bulk-import/",
        "Disallow: /api/v1/",
        "",
        "Sitemap: " + _abs(reverse('sitemap_xml')),
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    """Render an XML sitemap of the public pages on the canonical domain."""
    urls = []
    for name, priority, freq in SITEMAP_PAGES:
        loc = _abs(reverse(name))
        urls.append(
            "  <url>\n"
            "    <loc>{loc}</loc>\n"
            "    <changefreq>{freq}</changefreq>\n"
            "    <priority>{priority}</priority>\n"
            "  </url>".format(loc=loc, freq=freq, priority=priority)
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return HttpResponse(xml, content_type="application/xml")
