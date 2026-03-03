# synergy_data/context_processors.py
from .models import Antibiotic, Phytochemical, SiteViewCounter, SynergyExperiment


def view_counter(request):
    # get_or_create ensures we only ever have one counter object.
    counter, created = SiteViewCounter.objects.get_or_create(id=1)

    # Increment the count on every request and save it to the database
    counter.count += 1
    counter.save()

    # Return site-wide stats for the footer
    return {
        'total_views': counter.count,
        'total_experiments': SynergyExperiment.objects.count(),
        'total_phytochemicals': Phytochemical.objects.count(),
        'total_antibiotics': Antibiotic.objects.count(),
    }
