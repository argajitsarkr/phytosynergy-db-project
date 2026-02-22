import csv
from django.shortcuts import render
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from .models import Phytochemical, Antibiotic, Pathogen, SynergyExperiment, Source, AntibioticClass


def home_page(request):
    synergy_entries_count = SynergyExperiment.objects.count()
    phytochemical_count = Phytochemical.objects.count()
    source_count = Source.objects.count()
    antibiotic_count = Antibiotic.objects.count()
    eskape_pathogen_count = 6

    # Top phytochemicals by synergy experiment count
    top_phytochemicals = (
        Phytochemical.objects.annotate(exp_count=Count('synergyexperiment'))
        .order_by('-exp_count')[:5]
    )

    # Synergy breakdown for the homepage
    synergy_count = SynergyExperiment.objects.filter(interpretation='Synergy').count()
    additive_count = SynergyExperiment.objects.filter(interpretation='Additive').count()

    context = {
        'synergy_entries_count': synergy_entries_count,
        'phytochemical_count': phytochemical_count,
        'source_count': source_count,
        'antibiotic_count': antibiotic_count,
        'eskape_pathogen_count': eskape_pathogen_count,
        'top_phytochemicals': top_phytochemicals,
        'synergy_count': synergy_count,
        'additive_count': additive_count,
    }
    return render(request, 'synergy_data/home.html', context)


def about_page(request):
    return render(request, 'synergy_data/about.html')


def database_search_page(request):
    results = SynergyExperiment.objects.select_related(
        'phytochemical', 'antibiotic', 'antibiotic__antibiotic_class', 'pathogen', 'source'
    ).all()

    query = request.GET.get('query', '').strip()
    pathogen_id = request.GET.get('pathogen', '')
    antibiotic_id = request.GET.get('antibiotic', '')
    interpretation = request.GET.get('interpretation', '')
    abx_class_id = request.GET.get('abx_class', '')

    if query:
        results = results.filter(
            Q(phytochemical__compound_name__icontains=query) |
            Q(antibiotic__antibiotic_name__icontains=query) |
            Q(pathogen__genus__icontains=query) |
            Q(pathogen__species__icontains=query) |
            Q(pathogen__strain__icontains=query)
        )

    if pathogen_id:
        results = results.filter(pathogen_id=pathogen_id)

    if antibiotic_id:
        results = results.filter(antibiotic_id=antibiotic_id)

    if interpretation:
        results = results.filter(interpretation=interpretation)

    if abx_class_id:
        results = results.filter(antibiotic__antibiotic_class_id=abx_class_id)

    # Pagination (50 per page)
    from django.core.paginator import Paginator
    paginator = Paginator(results, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'results_count': results.count(),
        'pathogens': Pathogen.objects.order_by('genus', 'species').all(),
        'antibiotics': Antibiotic.objects.order_by('antibiotic_name').all(),
        'abx_classes': AntibioticClass.objects.order_by('class_name').all(),
        'interpretation_choices': SynergyExperiment.InterpretationChoices.choices,
        'search_query': query,
        'selected_pathogen': pathogen_id,
        'selected_antibiotic': antibiotic_id,
        'selected_interpretation': interpretation,
        'selected_abx_class': abx_class_id,
    }
    return render(request, 'synergy_data/database_search.html', context)


def download_data(request):
    """Download filtered results as CSV."""
    results = SynergyExperiment.objects.select_related(
        'phytochemical', 'antibiotic', 'antibiotic__antibiotic_class', 'pathogen', 'source'
    ).all()

    query = request.GET.get('query', '').strip()
    pathogen_id = request.GET.get('pathogen', '')
    antibiotic_id = request.GET.get('antibiotic', '')
    interpretation = request.GET.get('interpretation', '')
    abx_class_id = request.GET.get('abx_class', '')

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
    if interpretation:
        results = results.filter(interpretation=interpretation)
    if abx_class_id:
        results = results.filter(antibiotic__antibiotic_class_id=abx_class_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="phytosynergydb_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Source DOI', 'Publication Year', 'Journal',
        'Pathogen', 'Strain', 'Gram Stain',
        'Phytochemical', 'PubChem CID',
        'Antibiotic', 'Antibiotic Class',
        'MIC Phyto Alone', 'MIC ABX Alone',
        'MIC Phyto in Combo', 'MIC ABX in Combo', 'MIC Units',
        'FIC Index', 'Interpretation', 'Mechanism of Action', 'Notes',
    ])

    for exp in results:
        writer.writerow([
            exp.source.doi or '',
            exp.source.publication_year or '',
            exp.source.journal or '',
            f"{exp.pathogen.genus} {exp.pathogen.species}",
            exp.pathogen.strain or '',
            exp.pathogen.gram_stain or '',
            exp.phytochemical.compound_name,
            exp.phytochemical.pubchem_cid or '',
            exp.antibiotic.antibiotic_name,
            exp.antibiotic.antibiotic_class.class_name if exp.antibiotic.antibiotic_class else '',
            exp.mic_phyto_alone or '',
            exp.mic_abx_alone or '',
            exp.mic_phyto_in_combo or '',
            exp.mic_abx_in_combo or '',
            exp.mic_units,
            exp.fic_index or '',
            exp.interpretation or '',
            exp.moa_observed or '',
            exp.notes or '',
        ])

    return response


def stats_page(request):
    """Database statistics page with chart data."""
    total_experiments = SynergyExperiment.objects.count()
    total_phytochemicals = Phytochemical.objects.count()
    total_antibiotics = Antibiotic.objects.count()
    total_pathogens = Pathogen.objects.count()
    total_sources = Source.objects.count()

    # Experiments by interpretation
    interpretation_data = (
        SynergyExperiment.objects
        .values('interpretation')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Experiments by pathogen species
    pathogen_data = (
        SynergyExperiment.objects
        .values('pathogen__genus', 'pathogen__species')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Experiments by antibiotic
    antibiotic_data = (
        SynergyExperiment.objects
        .values('antibiotic__antibiotic_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Experiments by phytochemical (top 10)
    phytochemical_data = (
        SynergyExperiment.objects
        .values('phytochemical__compound_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    # Experiments by publication year
    year_data = (
        SynergyExperiment.objects
        .filter(source__publication_year__isnull=False)
        .values('source__publication_year')
        .annotate(count=Count('id'))
        .order_by('source__publication_year')
    )

    # Experiments by antibiotic class
    abx_class_data = (
        SynergyExperiment.objects
        .filter(antibiotic__antibiotic_class__isnull=False)
        .values('antibiotic__antibiotic_class__class_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    context = {
        'total_experiments': total_experiments,
        'total_phytochemicals': total_phytochemicals,
        'total_antibiotics': total_antibiotics,
        'total_pathogens': total_pathogens,
        'total_sources': total_sources,
        # JSON-serialisable lists for Chart.js
        'interpretation_labels': [d['interpretation'] or 'Unknown' for d in interpretation_data],
        'interpretation_values': [d['count'] for d in interpretation_data],
        'pathogen_labels': [f"{d['pathogen__genus']} {d['pathogen__species']}" for d in pathogen_data],
        'pathogen_values': [d['count'] for d in pathogen_data],
        'antibiotic_labels': [d['antibiotic__antibiotic_name'] for d in antibiotic_data],
        'antibiotic_values': [d['count'] for d in antibiotic_data],
        'phytochemical_labels': [d['phytochemical__compound_name'] for d in phytochemical_data],
        'phytochemical_values': [d['count'] for d in phytochemical_data],
        'year_labels': [d['source__publication_year'] for d in year_data],
        'year_values': [d['count'] for d in year_data],
        'abx_class_labels': [d['antibiotic__antibiotic_class__class_name'] for d in abx_class_data],
        'abx_class_values': [d['count'] for d in abx_class_data],
    }
    return render(request, 'synergy_data/stats.html', context)


def health_check(request):
    return HttpResponse("Health Check OK. The Django application is running.", status=200)
