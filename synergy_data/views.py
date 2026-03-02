from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import SynergyEntryForm
from .models import (
    Antibiotic,
    Pathogen,
    Phytochemical,
    Source,
    SynergyExperiment,
)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def parse_pathogen_name(full_name):
    """
    Parse a pathogen full name into (genus, species, strain).

    Examples:
        "Pseudomonas aeruginosa MTCC 2488" -> ("Pseudomonas", "aeruginosa", "MTCC 2488")
        "Staphylococcus aureus"             -> ("Staphylococcus", "aureus", None)
        "MRSA"                              -> ("MRSA", "", None)
    """
    parts = full_name.strip().split()
    if len(parts) >= 2:
        genus = parts[0]
        species = parts[1]
        strain = ' '.join(parts[2:]) if len(parts) > 2 else None
    elif len(parts) == 1:
        genus = parts[0]
        species = ''
        strain = None
    else:
        raise ValueError("Pathogen name cannot be empty")
    return genus, species, strain or None


def auto_calculate_fic(mic_phyto_alone, mic_abx_alone, mic_phyto_in_combo, mic_abx_in_combo):
    """
    FIC = (MIC_phyto_combo / MIC_phyto_alone) + (MIC_abx_combo / MIC_abx_alone)
    Returns None if any required value is missing or zero.
    """
    values = [mic_phyto_alone, mic_abx_alone, mic_phyto_in_combo, mic_abx_in_combo]
    if all(v is not None and v > 0 for v in values):
        return (mic_phyto_in_combo / mic_phyto_alone) + (mic_abx_in_combo / mic_abx_alone)
    return None


def auto_interpret_fic(fic_index):
    """Derive interpretation from FIC index value."""
    if fic_index is None:
        return None
    if fic_index <= Decimal('0.5'):
        return 'Synergy'
    elif fic_index <= Decimal('1.0'):
        return 'Additive'
    elif fic_index <= Decimal('4.0'):
        return 'Indifference'
    else:
        return 'Antagonism'


def get_or_create_case_insensitive(model, field_name, value):
    """
    Case-insensitive get_or_create for models with unique text fields.
    Handles race conditions with IntegrityError fallback.
    """
    lookup = {f'{field_name}__iexact': value}
    try:
        return model.objects.get(**lookup)
    except model.DoesNotExist:
        try:
            return model.objects.create(**{field_name: value})
        except IntegrityError:
            return model.objects.get(**lookup)


# ==============================================================================
# HOME PAGE
# ==============================================================================

def home_page(request):
    synergy_entries_count = SynergyExperiment.objects.count()
    phytochemical_count = Phytochemical.objects.count()
    antibiotic_count = Antibiotic.objects.count()
    source_count = Source.objects.count()
    eskape_pathogen_count = 6
    synergy_confirmed_count = SynergyExperiment.objects.filter(
        interpretation='Synergy'
    ).count()

    # ESKAPE pathogen data with per-genus experiment counts
    eskape_data = [
        {'letter': 'E', 'name': 'Enterococcus faecium', 'genus': 'Enterococcus', 'gram': 'Gram-positive'},
        {'letter': 'S', 'name': 'Staphylococcus aureus', 'genus': 'Staphylococcus', 'gram': 'Gram-positive'},
        {'letter': 'K', 'name': 'Klebsiella pneumoniae', 'genus': 'Klebsiella', 'gram': 'Gram-negative'},
        {'letter': 'A', 'name': 'Acinetobacter baumannii', 'genus': 'Acinetobacter', 'gram': 'Gram-negative'},
        {'letter': 'P', 'name': 'Pseudomonas aeruginosa', 'genus': 'Pseudomonas', 'gram': 'Gram-negative'},
        {'letter': 'E', 'name': 'Enterobacter spp.', 'genus': 'Enterobacter', 'gram': 'Gram-negative'},
    ]
    for p in eskape_data:
        p['count'] = SynergyExperiment.objects.filter(pathogen__genus=p['genus']).count()

    # Recent entries for the homepage
    recent_entries = SynergyExperiment.objects.select_related(
        'phytochemical', 'antibiotic', 'pathogen', 'source'
    ).order_by('-id')[:5]

    context = {
        'synergy_entries_count': synergy_entries_count,
        'phytochemical_count': phytochemical_count,
        'antibiotic_count': antibiotic_count,
        'source_count': source_count,
        'eskape_pathogen_count': eskape_pathogen_count,
        'synergy_confirmed_count': synergy_confirmed_count,
        'eskape_data': eskape_data,
        'recent_entries': recent_entries,
    }
    return render(request, 'synergy_data/home.html', context)


# ==============================================================================
# ABOUT PAGE
# ==============================================================================

def about_page(request):
    return render(request, 'synergy_data/about.html')


# ==============================================================================
# DATABASE SEARCH PAGE
# ==============================================================================

def database_search_page(request):
    results = SynergyExperiment.objects.select_related(
        'phytochemical', 'antibiotic', 'pathogen', 'source'
    ).all()

    query = request.GET.get('query')
    pathogen_id = request.GET.get('pathogen')
    antibiotic_id = request.GET.get('antibiotic')
    mechanism = request.GET.get('mechanism')

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

    context = {
        'results': results,
        'pathogens': Pathogen.objects.order_by('genus', 'species').all(),
        'antibiotics': Antibiotic.objects.order_by('antibiotic_name').all(),
        'mechanisms': SynergyExperiment.objects.values_list(
            'moa_observed', flat=True
        ).distinct().exclude(moa_observed__isnull=True).exclude(moa_observed__exact=''),
        'search_query': query or "",
        'selected_pathogen': pathogen_id,
        'selected_antibiotic': antibiotic_id,
        'selected_mechanism': mechanism,
    }
    return render(request, 'synergy_data/database_search.html', context)


# ==============================================================================
# DATA ENTRY PAGE (login-protected)
# ==============================================================================

@login_required
def data_entry_view(request):
    if request.method == 'POST':
        form = SynergyEntryForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            # 1. Resolve Source (get_or_create by DOI)
            doi = cd['source_doi'].strip()
            source, _ = Source.objects.get_or_create(doi=doi)

            # 2. Resolve Pathogen (parse name, then get_or_create)
            genus, species, strain = parse_pathogen_name(cd['pathogen_full_name'])
            pathogen, _ = Pathogen.objects.get_or_create(
                genus=genus, species=species, strain=strain
            )

            # 3. Resolve Phytochemical (case-insensitive)
            phytochemical = get_or_create_case_insensitive(
                Phytochemical, 'compound_name', cd['phytochemical_name'].strip()
            )

            # 4. Resolve Antibiotic (case-insensitive)
            antibiotic = get_or_create_case_insensitive(
                Antibiotic, 'antibiotic_name', cd['antibiotic_name'].strip()
            )

            # 5. Auto-calculate FIC if not provided
            fic_index = cd.get('fic_index')
            if fic_index is None:
                fic_index = auto_calculate_fic(
                    cd.get('mic_phyto_alone'),
                    cd.get('mic_abx_alone'),
                    cd.get('mic_phyto_in_combo'),
                    cd.get('mic_abx_in_combo'),
                )

            # 6. Auto-interpret if not provided
            interpretation = cd.get('interpretation') or auto_interpret_fic(fic_index)

            # 7. Create the experiment record
            experiment = SynergyExperiment.objects.create(
                phytochemical=phytochemical,
                antibiotic=antibiotic,
                pathogen=pathogen,
                source=source,
                mic_phyto_alone=cd.get('mic_phyto_alone'),
                mic_abx_alone=cd.get('mic_abx_alone'),
                mic_phyto_in_combo=cd.get('mic_phyto_in_combo'),
                mic_abx_in_combo=cd.get('mic_abx_in_combo'),
                mic_units=cd.get('mic_units') or '\u00b5g/mL',
                fic_index=fic_index,
                interpretation=interpretation,
                moa_observed=cd.get('moa_observed', ''),
                notes=cd.get('notes', ''),
            )

            fic_display = f"{fic_index:.4f}" if fic_index else "N/A"
            messages.success(
                request,
                f"Entry saved: {experiment}. FIC={fic_display}, "
                f"Interpretation={interpretation or 'N/A'}"
            )

            # "Save & Add Another" pre-fills DOI and MIC units for convenience
            if 'save_and_another' in request.POST:
                form = SynergyEntryForm(initial={
                    'source_doi': doi,
                    'mic_units': cd.get('mic_units') or '\u00b5g/mL',
                })
            else:
                return redirect('database_search')
    else:
        form = SynergyEntryForm()

    return render(request, 'synergy_data/data_entry.html', {'form': form})


# ==============================================================================
# DATA DOWNLOAD (placeholder)
# ==============================================================================

def download_data(request):
    pass


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

def health_check(request):
    """A simple view that proves the Django app is running."""
    return HttpResponse("Health Check OK. The Django application is running.", status=200)
