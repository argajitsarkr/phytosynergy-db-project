# synergy_data/views.py

from django.shortcuts import render
from django.db.models import Q
from .models import Phytochemical, Antibiotic, Pathogen, SynergyExperiment, Source

# View for the new, modern homepage
def home_page(request):
    # Calculate the stats for the homepage
    synergy_entries_count = SynergyExperiment.objects.count()
    phytochemical_count = Phytochemical.objects.count()
    source_count = Source.objects.count()
    eskape_pathogen_count = 6 # This is a fixed value for our project

    context = {
        'synergy_entries_count': synergy_entries_count,
        'phytochemical_count': phytochemical_count,
        'source_count': source_count,
        'eskape_pathogen_count': eskape_pathogen_count,
    }
    return render(request, 'synergy_data/home.html', context)

# View for the About page
def about_page(request):
    # You can add team member info here later
    return render(request, 'synergy_data/about.html')

# The main view for our powerful database search page
def database_search_page(request):
    # Use select_related for a massive performance boost by pre-fetching related objects
    results = SynergyExperiment.objects.select_related('phytochemical', 'antibiotic', 'pathogen', 'source').all()

    # Get filter values from the user's GET request
    query = request.GET.get('query')
    pathogen_id = request.GET.get('pathogen')
    antibiotic_id = request.GET.get('antibiotic')
    mechanism = request.GET.get('mechanism')

    # Apply filters if they exist
    if query:
        results = results.filter(
            Q(phytochemical__compound_name__icontains=query) |
            Q(antibiotic__antibiotic_name__icontains=query) |
            Q(pathogen__genus__icontains=query) |
            Q(pathogen__species__icontains=query)
        )
    
    if pathogen_id:
        results = results.filter(pathogen_id=pathogen_id)
    
    if antibiotic_id:
        results = results.filter(antibiotic_id=antibiotic_id)

    if mechanism:
        results = results.filter(moa_observed__icontains=mechanism)

    # Prepare the context dictionary to pass to the template
    context = {
        'results': results,
        'pathogens': Pathogen.objects.order_by('genus', 'species').all(),
        'antibiotics': Antibiotic.objects.order_by('antibiotic_name').all(),
        'mechanisms': SynergyExperiment.objects.values_list('moa_observed', flat=True).distinct().exclude(moa_observed__isnull=True).exclude(moa_observed__exact=''),
        'search_query': query or "",
        'selected_pathogen': pathogen_id,
        'selected_antibiotic': antibiotic_id,
        'selected_mechanism': mechanism,
    }
    return render(request, 'synergy_data/database_search.html', context)

# Placeholder for the data download feature
def download_data(request):
    pass