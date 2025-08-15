from django.contrib import admin
from .models import (
    AntibioticClass,
    Phytochemical,
    Antibiotic,
    Pathogen,
    Source,
    SynergyExperiment
)

# -----------------------------------------------------------------------------
# We register the "lookup" tables with a simple registration.
# -----------------------------------------------------------------------------
admin.site.register(AntibioticClass)
admin.site.register(Phytochemical)
admin.site.register(Antibiotic)
admin.site.register(Pathogen)
admin.site.register(Source)


# -----------------------------------------------------------------------------
# For our main SynergyExperiment table, we create a custom Admin class.
# This makes it powerful and easy to use for data curation.
# -----------------------------------------------------------------------------
@admin.register(SynergyExperiment)
class SynergyExperimentAdmin(admin.ModelAdmin):
    """
    Customizes the display of the SynergyExperiment table in the Django admin.
    """
    
    # This controls which columns are shown in the main list view.
    list_display = (
        'phytochemical', 
        'antibiotic', 
        'pathogen', 
        'fic_index', 
        'interpretation', 
        'source'
    )
    
    # This adds a powerful filtering sidebar on the right.
    # Note: We filter by 'antibiotic__antibiotic_class' for a smarter filter.
    list_filter = (
        'interpretation', 
        'pathogen', 
        'antibiotic__antibiotic_class'
    )
    
    # This adds a search bar at the top to find specific entries.
    search_fields = (
        'phytochemical__compound_name', 
        'antibiotic__antibiotic_name', 
        'pathogen__species',
        'source__doi'
    )

    # --- THIS IS THE CRITICAL PERFORMANCE OPTIMIZATION ---
    # This tells Django to fetch all related objects in a single database query,
    # making the page load much, much faster with lots of data.
    list_select_related = ('phytochemical', 'antibiotic', 'pathogen', 'source')