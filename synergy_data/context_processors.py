# synergy_data/context_processors.py
from django.conf import settings
from django.db.models import F

from .models import Antibiotic, Phytochemical, SiteViewCounter, SynergyExperiment


def seo(request):
    """Expose the canonical site URL and search-engine verification tokens to
    every template for SEO tags (canonical link, Open Graph / Twitter URLs,
    JSON-LD, ownership-verification meta tags)."""
    return {
        'SITE_URL': settings.SITE_URL,
        'GOOGLE_SITE_VERIFICATION': settings.GOOGLE_SITE_VERIFICATION,
        'BING_SITE_VERIFICATION': settings.BING_SITE_VERIFICATION,
    }


def view_counter(request):
    counter, _ = SiteViewCounter.objects.get_or_create(id=1)

    # Mark this session as counted exactly once -> unique visitor.
    is_new_visitor = False
    try:
        if not request.session.get('counted_visitor'):
            if not request.session.session_key:
                request.session.save()
            request.session['counted_visitor'] = True
            is_new_visitor = True
    except Exception:
        # If session middleware is unavailable, skip visitor accounting.
        is_new_visitor = False

    update_kwargs = {'count': F('count') + 1}
    if is_new_visitor:
        update_kwargs['unique_visitors'] = F('unique_visitors') + 1
    SiteViewCounter.objects.filter(id=counter.id).update(**update_kwargs)
    counter.refresh_from_db()

    return {
        'total_views': counter.count,
        'total_visitors': counter.unique_visitors,
        'total_experiments': SynergyExperiment.objects.count(),
        'total_phytochemicals': Phytochemical.objects.count(),
        'total_antibiotics': Antibiotic.objects.count(),
    }
