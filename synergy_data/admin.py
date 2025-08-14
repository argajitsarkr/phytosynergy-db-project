from django.contrib import admin
from .models import (
    AntibioticClass,
    Phytochemical,
    Antibiotic,
    Pathogen,
    Source,
    SynergyExperiment
)

# Register your models here.

# A simple registration will work for most models
admin.site.register(AntibioticClass)
admin.site.register(Phytochemical)
admin.site.register(Antibiotic)
admin.site.register(Pathogen)
admin.site.register(Source)

# We can create a more customized view for the main data table
@admin.register(SynergyExperiment)
class SynergyExperimentAdmin(admin.ModelAdmin):
    # This shows useful columns in the main list view
    list_display = ('phytochemical', 'antibiotic', 'pathogen', 'fic_index', 'interpretation', 'source')
    # This adds filter options on the side
    list_filter = ('interpretation', 'pathogen', 'antibiotic', 'phytochemical')
    # This adds a search bar
    search_fields = ('source__doi', 'phytochemical__compound_name', 'antibiotic__antibiotic_name', 'pathogen__strain')