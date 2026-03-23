import csv
import json
import logging
import os
import re
import tempfile
import time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .forms import SynergyEntryForm
from .models import (
    Antibiotic,
    AntibioticClass,
    Pathogen,
    Phytochemical,
    Plant,
    Source,
    SynergyExperiment,
)
from .pubchem_utils import enrich_phytochemical

logger = logging.getLogger(__name__)


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


def _apply_search_filters(results, request):
    """Apply all search/filter parameters from the request to the queryset."""
    query = request.GET.get('query')
    pathogen_id = request.GET.get('pathogen')
    antibiotic_id = request.GET.get('antibiotic')
    mechanism = request.GET.get('mechanism')
    interpretation = request.GET.get('interpretation')
    eskape = request.GET.get('eskape')
    chemical_class = request.GET.get('chemical_class')

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

    if interpretation:
        results = results.filter(interpretation=interpretation)

    if eskape:
        results = results.filter(pathogen__genus__iexact=eskape)

    if chemical_class:
        results = results.filter(phytochemical__chemical_class__iexact=chemical_class)

    return results


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

    results = _apply_search_filters(results, request)

    # Get distinct chemical classes for filter dropdown
    chemical_classes = (
        Phytochemical.objects.values_list('chemical_class', flat=True)
        .exclude(chemical_class__isnull=True)
        .exclude(chemical_class__exact='')
        .distinct()
        .order_by('chemical_class')
    )

    context = {
        'results': results,
        'pathogens': Pathogen.objects.order_by('genus', 'species').all(),
        'antibiotics': Antibiotic.objects.order_by('antibiotic_name').all(),
        'mechanisms': SynergyExperiment.objects.values_list(
            'moa_observed', flat=True
        ).distinct().exclude(moa_observed__isnull=True).exclude(moa_observed__exact=''),
        'chemical_classes': chemical_classes,
        'search_query': request.GET.get('query', ''),
        'selected_pathogen': request.GET.get('pathogen'),
        'selected_antibiotic': request.GET.get('antibiotic'),
        'selected_mechanism': request.GET.get('mechanism'),
        'selected_interpretation': request.GET.get('interpretation'),
        'selected_eskape': request.GET.get('eskape'),
        'selected_chemical_class': request.GET.get('chemical_class'),
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

            # 1. Resolve Source (get_or_create by DOI, update metadata)
            doi = cd['source_doi'].strip()
            source, _ = Source.objects.get_or_create(doi=doi)
            # Update source metadata if provided (fills blanks)
            source_updated = False
            if cd.get('publication_year') and not source.publication_year:
                source.publication_year = cd['publication_year']
                source_updated = True
            if cd.get('article_title') and not source.article_title:
                source.article_title = cd['article_title'].strip()
                source_updated = True
            if cd.get('journal') and not source.journal:
                source.journal = cd['journal'].strip()
                source_updated = True
            if source_updated:
                source.save()

            # 2. Resolve Pathogen (parse name, then get_or_create)
            genus, species, strain = parse_pathogen_name(cd['pathogen_full_name'])
            pathogen, _ = Pathogen.objects.get_or_create(
                genus=genus, species=species, strain=strain
            )

            # 3. Resolve Phytochemical (case-insensitive)
            phytochemical = get_or_create_case_insensitive(
                Phytochemical, 'compound_name', cd['phytochemical_name'].strip()
            )

            # 3b. Auto-enrich phytochemical with PubChem + ClassyFire data
            enrichment_status = enrich_phytochemical(phytochemical)

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
            enrichment_parts = []
            if enrichment_status.get("pubchem"):
                enrichment_parts.append("\u2713 PubChem enriched")
            if enrichment_status.get("classyfire"):
                enrichment_parts.append("\u2713 ClassyFire classified")
            enrichment_msg = (" | " + " | ".join(enrichment_parts)) if enrichment_parts else ""
            messages.success(
                request,
                f"Entry saved: {experiment}. FIC={fic_display}, "
                f"Interpretation={interpretation or 'N/A'}{enrichment_msg}"
            )

            # "Save & Add Another" pre-fills DOI, year, journal and MIC units
            if 'save_and_another' in request.POST:
                form = SynergyEntryForm(initial={
                    'source_doi': doi,
                    'publication_year': cd.get('publication_year'),
                    'article_title': cd.get('article_title'),
                    'journal': cd.get('journal'),
                    'mic_units': cd.get('mic_units') or '\u00b5g/mL',
                })
            else:
                return redirect('database_search')
    else:
        form = SynergyEntryForm()

    return render(request, 'synergy_data/data_entry.html', {'form': form})


# ==============================================================================
# EDIT ENTRY PAGE (login-protected)
# ==============================================================================

@login_required
def edit_entry_view(request, pk):
    """Edit an existing synergy experiment record."""
    from django.shortcuts import get_object_or_404

    experiment = get_object_or_404(
        SynergyExperiment.objects.select_related(
            'phytochemical', 'antibiotic', 'pathogen', 'source'
        ),
        pk=pk,
    )

    if request.method == 'POST':
        form = SynergyEntryForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            # 1. Resolve Source
            doi = cd['source_doi'].strip()
            source, _ = Source.objects.get_or_create(doi=doi)
            source_updated = False
            if cd.get('publication_year'):
                source.publication_year = cd['publication_year']
                source_updated = True
            if cd.get('article_title'):
                source.article_title = cd['article_title'].strip()
                source_updated = True
            if cd.get('journal'):
                source.journal = cd['journal'].strip()
                source_updated = True
            if source_updated:
                source.save()

            # 2. Resolve Pathogen
            genus, species, strain = parse_pathogen_name(cd['pathogen_full_name'])
            pathogen, _ = Pathogen.objects.get_or_create(
                genus=genus, species=species, strain=strain
            )

            # 3. Resolve Phytochemical
            phytochemical = get_or_create_case_insensitive(
                Phytochemical, 'compound_name', cd['phytochemical_name'].strip()
            )

            # 3b. Auto-enrich
            enrichment_status = enrich_phytochemical(phytochemical)

            # 4. Resolve Antibiotic
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

            # 6. Auto-interpret
            interpretation = cd.get('interpretation') or auto_interpret_fic(fic_index)

            # 7. Update the experiment record (not create!)
            experiment.phytochemical = phytochemical
            experiment.antibiotic = antibiotic
            experiment.pathogen = pathogen
            experiment.source = source
            experiment.mic_phyto_alone = cd.get('mic_phyto_alone')
            experiment.mic_abx_alone = cd.get('mic_abx_alone')
            experiment.mic_phyto_in_combo = cd.get('mic_phyto_in_combo')
            experiment.mic_abx_in_combo = cd.get('mic_abx_in_combo')
            experiment.mic_units = cd.get('mic_units') or '\u00b5g/mL'
            experiment.fic_index = fic_index
            experiment.interpretation = interpretation
            experiment.moa_observed = cd.get('moa_observed', '')
            experiment.notes = cd.get('notes', '')
            experiment.save()

            fic_display = f"{fic_index:.4f}" if fic_index else "N/A"
            enrichment_parts = []
            if enrichment_status.get("pubchem"):
                enrichment_parts.append("\u2713 PubChem enriched")
            if enrichment_status.get("classyfire"):
                enrichment_parts.append("\u2713 ClassyFire classified")
            enrichment_msg = (" | " + " | ".join(enrichment_parts)) if enrichment_parts else ""
            messages.success(
                request,
                f"Entry updated: {experiment}. FIC={fic_display}, "
                f"Interpretation={interpretation or 'N/A'}{enrichment_msg}"
            )
            return redirect('database_search')
    else:
        # Pre-populate form with existing data
        pathogen_str = f"{experiment.pathogen.genus} {experiment.pathogen.species}"
        if experiment.pathogen.strain:
            pathogen_str += f" {experiment.pathogen.strain}"

        form = SynergyEntryForm(initial={
            'source_doi': experiment.source.doi or '',
            'publication_year': experiment.source.publication_year,
            'article_title': experiment.source.article_title or '',
            'journal': experiment.source.journal or '',
            'pathogen_full_name': pathogen_str,
            'phytochemical_name': experiment.phytochemical.compound_name,
            'antibiotic_name': experiment.antibiotic.antibiotic_name,
            'mic_phyto_alone': experiment.mic_phyto_alone,
            'mic_abx_alone': experiment.mic_abx_alone,
            'mic_phyto_in_combo': experiment.mic_phyto_in_combo,
            'mic_abx_in_combo': experiment.mic_abx_in_combo,
            'mic_units': experiment.mic_units or '\u00b5g/mL',
            'fic_index': experiment.fic_index,
            'interpretation': experiment.interpretation or '',
            'moa_observed': experiment.moa_observed or '',
            'notes': experiment.notes or '',
        })

    return render(request, 'synergy_data/data_entry.html', {
        'form': form,
        'editing': True,
        'experiment_id': pk,
    })


# ==============================================================================
# DATA DOWNLOAD (CSV Export)
# ==============================================================================

def download_data(request):
    """Export synergy experiment data as CSV."""
    if request.method == 'GET' and 'export' in request.GET:
        # Build queryset with filters
        results = SynergyExperiment.objects.select_related(
            'phytochemical', 'antibiotic', 'pathogen', 'source'
        ).all()
        results = _apply_search_filters(results, request)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="phytosynergydb_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Phytochemical', 'PubChem_CID', 'InChI_Key', 'SMILES',
            'Molecular_Formula', 'Molecular_Weight', 'XLogP',
            'HBond_Donors', 'HBond_Acceptors', 'TPSA', 'Rotatable_Bonds',
            'Lipinski_Pass', 'Chemical_Superclass', 'Chemical_Class', 'Chemical_Subclass',
            'Antibiotic', 'DrugBank_ID', 'Antibiotic_Class',
            'Pathogen_Genus', 'Pathogen_Species', 'Pathogen_Strain', 'Gram_Stain',
            'MIC_Phyto_Alone', 'MIC_Abx_Alone', 'MIC_Phyto_Combo', 'MIC_Abx_Combo', 'MIC_Units',
            'FIC_Index', 'Interpretation',
            'Mechanism_of_Action', 'Notes',
            'DOI', 'PMID', 'Journal', 'Publication_Year',
        ])

        for exp in results:
            lipinski = exp.phytochemical.passes_lipinski
            lipinski_str = ''
            if lipinski is True:
                lipinski_str = 'Yes'
            elif lipinski is False:
                lipinski_str = 'No'

            writer.writerow([
                exp.phytochemical.compound_name,
                exp.phytochemical.pubchem_cid or '',
                exp.phytochemical.inchi_key or '',
                exp.phytochemical.canonical_smiles or '',
                exp.phytochemical.molecular_formula or '',
                exp.phytochemical.molecular_weight or '',
                exp.phytochemical.xlogp if exp.phytochemical.xlogp is not None else '',
                exp.phytochemical.hbd if exp.phytochemical.hbd is not None else '',
                exp.phytochemical.hba if exp.phytochemical.hba is not None else '',
                exp.phytochemical.tpsa if exp.phytochemical.tpsa is not None else '',
                exp.phytochemical.rotatable_bonds if exp.phytochemical.rotatable_bonds is not None else '',
                lipinski_str,
                exp.phytochemical.chemical_superclass or '',
                exp.phytochemical.chemical_class or '',
                exp.phytochemical.chemical_subclass or '',
                exp.antibiotic.antibiotic_name,
                exp.antibiotic.drugbank_id or '',
                exp.antibiotic.antibiotic_class.class_name if exp.antibiotic.antibiotic_class else '',
                exp.pathogen.genus,
                exp.pathogen.species,
                exp.pathogen.strain or '',
                exp.pathogen.gram_stain or '',
                exp.mic_phyto_alone or '',
                exp.mic_abx_alone or '',
                exp.mic_phyto_in_combo or '',
                exp.mic_abx_in_combo or '',
                exp.mic_units,
                exp.fic_index or '',
                exp.interpretation or '',
                exp.moa_observed or '',
                exp.notes or '',
                exp.source.doi or '',
                exp.source.pmid or '',
                exp.source.journal or '',
                exp.source.publication_year or '',
            ])

        return response

    # Show download page
    total_experiments = SynergyExperiment.objects.count()
    total_synergies = SynergyExperiment.objects.filter(interpretation='Synergy').count()
    return render(request, 'synergy_data/download.html', {
        'total_experiments': total_experiments,
        'total_synergies': total_synergies,
    })


# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================

def api_experiments(request):
    """JSON API endpoint for synergy experiments."""
    results = SynergyExperiment.objects.select_related(
        'phytochemical', 'antibiotic', 'pathogen', 'source'
    ).all()

    results = _apply_search_filters(results, request)

    # Pagination
    try:
        limit = min(int(request.GET.get('limit', 100)), 500)
    except (ValueError, TypeError):
        limit = 100
    try:
        offset = max(int(request.GET.get('offset', 0)), 0)
    except (ValueError, TypeError):
        offset = 0

    total_count = results.count()
    page_results = results[offset:offset + limit]

    data = []
    for exp in page_results:
        data.append({
            'id': exp.id,
            'phytochemical': {
                'name': exp.phytochemical.compound_name,
                'pubchem_cid': exp.phytochemical.pubchem_cid,
                'inchi_key': exp.phytochemical.inchi_key,
                'smiles': exp.phytochemical.canonical_smiles,
                'molecular_weight': str(exp.phytochemical.molecular_weight) if exp.phytochemical.molecular_weight else None,
                'molecular_formula': exp.phytochemical.molecular_formula,
                'xlogp': exp.phytochemical.xlogp,
                'hbd': exp.phytochemical.hbd,
                'hba': exp.phytochemical.hba,
                'tpsa': exp.phytochemical.tpsa,
                'rotatable_bonds': exp.phytochemical.rotatable_bonds,
                'passes_lipinski': exp.phytochemical.passes_lipinski,
                'chemical_superclass': exp.phytochemical.chemical_superclass,
                'chemical_class': exp.phytochemical.chemical_class,
                'chemical_subclass': exp.phytochemical.chemical_subclass,
            },
            'antibiotic': {
                'name': exp.antibiotic.antibiotic_name,
                'drugbank_id': exp.antibiotic.drugbank_id,
                'class': exp.antibiotic.antibiotic_class.class_name if exp.antibiotic.antibiotic_class else None,
            },
            'pathogen': {
                'genus': exp.pathogen.genus,
                'species': exp.pathogen.species,
                'strain': exp.pathogen.strain,
                'gram_stain': exp.pathogen.gram_stain,
            },
            'mic_phyto_alone': str(exp.mic_phyto_alone) if exp.mic_phyto_alone else None,
            'mic_abx_alone': str(exp.mic_abx_alone) if exp.mic_abx_alone else None,
            'mic_phyto_in_combo': str(exp.mic_phyto_in_combo) if exp.mic_phyto_in_combo else None,
            'mic_abx_in_combo': str(exp.mic_abx_in_combo) if exp.mic_abx_in_combo else None,
            'mic_units': exp.mic_units,
            'fic_index': str(exp.fic_index) if exp.fic_index else None,
            'interpretation': exp.interpretation,
            'mechanism_of_action': exp.moa_observed,
            'source': {
                'doi': exp.source.doi,
                'pmid': exp.source.pmid,
                'journal': exp.source.journal,
                'year': exp.source.publication_year,
                'title': exp.source.article_title,
            },
        })

    return JsonResponse({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': data,
    })


def api_statistics(request):
    """JSON API endpoint for database statistics."""
    synergy_count = SynergyExperiment.objects.filter(interpretation='Synergy').count()
    additive_count = SynergyExperiment.objects.filter(interpretation='Additive').count()
    indifference_count = SynergyExperiment.objects.filter(interpretation='Indifference').count()
    antagonism_count = SynergyExperiment.objects.filter(interpretation='Antagonism').count()

    eskape_stats = {}
    for genus in ['Enterococcus', 'Staphylococcus', 'Klebsiella', 'Acinetobacter', 'Pseudomonas', 'Enterobacter']:
        eskape_stats[genus] = SynergyExperiment.objects.filter(pathogen__genus=genus).count()

    return JsonResponse({
        'total_experiments': SynergyExperiment.objects.count(),
        'total_phytochemicals': Phytochemical.objects.count(),
        'total_antibiotics': Antibiotic.objects.count(),
        'total_sources': Source.objects.count(),
        'total_pathogens': Pathogen.objects.count(),
        'interpretations': {
            'synergy': synergy_count,
            'additive': additive_count,
            'indifference': indifference_count,
            'antagonism': antagonism_count,
        },
        'eskape_counts': eskape_stats,
    })


def api_docs(request):
    """API documentation page."""
    return render(request, 'synergy_data/api_docs.html')


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

def health_check(request):
    """A simple view that proves the Django app is running."""
    return HttpResponse("Health Check OK. The Django application is running.", status=200)


# ==============================================================================
# AI-ASSISTED PDF DATA EXTRACTION
# ==============================================================================

EXTRACTION_PROMPT = """You are a scientific data extraction specialist for an antimicrobial synergy database called PhytoSynergyDB.

Your task: Extract ALL synergy experiment data from this research paper. The paper studies combinations of phytochemicals (plant-derived compounds) with conventional antibiotics against bacterial pathogens.

EXTRACT THE FOLLOWING FOR EACH UNIQUE EXPERIMENT (one row per phytochemical x antibiotic x pathogen strain combination):

1. **source_doi**: The DOI of this paper (look in the header, footer, or references section). Format: "10.xxxx/xxxxx"
2. **source_pmid**: PubMed ID if available (often in the header). Integer only.
3. **publication_year**: Year of publication. Integer.
4. **journal**: Name of the journal.
5. **article_title**: Full title of the paper.
6. **pathogen_name**: Full taxonomic name with strain, e.g., "Staphylococcus aureus ATCC 25923". Include the strain/collection number if given.
7. **phytochemical_name**: Name of the plant-derived compound or extract. Use the most specific name available (prefer pure compound names over "extract of X plant"). If only crude/fraction extracts are tested, use the name as given (e.g., "Methanol extract of Syzygium aromaticum").
8. **plant_source**: The plant from which the phytochemical is derived, if mentioned. Scientific name preferred. e.g., "Syzygium aromaticum"
9. **antibiotic_name**: Name of the conventional antibiotic. Use standard names (e.g., "Ciprofloxacin" not "CIP").
10. **antibiotic_class**: Class of the antibiotic if mentioned (e.g., "Fluoroquinolone", "Beta-lactam", "Aminoglycoside").
11. **mic_phyto_alone**: MIC of the phytochemical when tested alone. Numeric value only.
12. **mic_abx_alone**: MIC of the antibiotic when tested alone. Numeric value only.
13. **mic_phyto_in_combo**: MIC of the phytochemical when used in combination. Numeric value only.
14. **mic_abx_in_combo**: MIC of the antibiotic when used in combination. Numeric value only.
15. **mic_units**: Units for ALL MIC values in this row (must be consistent). Usually "ug/mL" or "mg/L".
16. **fic_index**: FIC Index value if explicitly reported in the paper. Numeric value.
17. **interpretation**: Synergy interpretation if explicitly stated. One of: "Synergy", "Additive", "Indifference", "Antagonism".
18. **assay_method**: The experimental method used. One of: "checkerboard", "time_kill", "disk_diffusion", "broth_microdilution", "other".
19. **moa_observed**: Any mechanism of action described (e.g., "Efflux pump inhibition", "Biofilm disruption", "Membrane permeabilization"). Leave empty if not discussed.
20. **notes**: Any important caveats (e.g., "Crude extract, not pure compound", "Clinical isolate", "MIC reported as range 32-64, midpoint used").

RULES:
- Create ONE JSON object per unique combination (phytochemical x antibiotic x pathogen strain).
- If a paper tests 3 phytochemicals x 2 antibiotics x 4 strains, you should output 24 JSON objects.
- If MIC values are given as ranges (e.g., "32-64"), use the HIGHER value and note this in "notes".
- If MIC values are given as inequalities (e.g., ">256"), use the number (256) and note ">256" in notes.
- Convert all MIC values to the SAME unit within each row.
- If the paper only reports FIC index without individual MIC values, still extract the FIC and interpretation -- leave MIC fields as null.
- Do NOT invent data. If a value is not in the paper, set it to null.
- For crude/fraction extracts, set phytochemical_name to the extract description and note "Crude extract" in notes.

OUTPUT FORMAT:
Return ONLY a valid JSON array. No markdown, no explanation, no preamble. Just the JSON array.

Example output format:
[
  {{
    "source_doi": "10.1016/j.phymed.2023.154789",
    "source_pmid": null,
    "publication_year": 2023,
    "journal": "Phytomedicine",
    "article_title": "Synergistic effects of...",
    "pathogen_name": "Staphylococcus aureus ATCC 25923",
    "phytochemical_name": "Berberine",
    "plant_source": "Berberis vulgaris",
    "antibiotic_name": "Ciprofloxacin",
    "antibiotic_class": "Fluoroquinolone",
    "mic_phyto_alone": 64.0,
    "mic_abx_alone": 0.5,
    "mic_phyto_in_combo": 16.0,
    "mic_abx_in_combo": 0.125,
    "mic_units": "ug/mL",
    "fic_index": 0.5,
    "interpretation": "Synergy",
    "assay_method": "checkerboard",
    "moa_observed": "Efflux pump inhibition (NorA)",
    "notes": null
  }}
]

HERE IS THE PAPER TEXT:
---
{paper_text}
---

Extract ALL experiments from this paper now. Return ONLY the JSON array."""


def _extract_text_from_pdf(pdf_file):
    """Extract text from an uploaded PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    # Save uploaded file to a temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        for chunk in pdf_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(page.get_text())
        doc.close()
        return '\n'.join(text_parts)
    finally:
        os.unlink(tmp_path)


def _call_gemini_api(paper_text):
    """Send extracted text to Gemini API and get structured JSON back."""
    import google.generativeai as genai

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = EXTRACTION_PROMPT.format(paper_text=paper_text[:80000])  # Truncate to stay within limits

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
        ),
    )

    raw_text = response.text.strip()

    # Strip markdown fences if present
    if raw_text.startswith('```'):
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

    return json.loads(raw_text)


def _safe_decimal(value):
    """Convert a value to Decimal safely, returning None on failure."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _save_extracted_experiments(experiments_data):
    """
    Save a list of extracted experiment dicts to the database.
    Uses the same entity resolution logic as data_entry_view.
    Returns (saved_count, errors_list).
    """
    saved_count = 0
    errors = []

    for i, exp in enumerate(experiments_data):
        try:
            # 1. Resolve Source by DOI
            doi = (exp.get('source_doi') or '').strip()
            if not doi:
                errors.append(f"Row {i+1}: No DOI provided, skipping.")
                continue

            source, _ = Source.objects.get_or_create(doi=doi)
            source_updated = False
            pmid = exp.get('source_pmid')
            if pmid and not source.pmid:
                try:
                    source.pmid = int(pmid)
                    source_updated = True
                except (ValueError, TypeError):
                    pass
            if exp.get('publication_year') and not source.publication_year:
                try:
                    source.publication_year = int(exp['publication_year'])
                    source_updated = True
                except (ValueError, TypeError):
                    pass
            if exp.get('article_title') and not source.article_title:
                source.article_title = exp['article_title'].strip()
                source_updated = True
            if exp.get('journal') and not source.journal:
                source.journal = exp['journal'].strip()
                source_updated = True
            if source_updated:
                source.save()

            # 2. Resolve Pathogen
            pathogen_name = (exp.get('pathogen_name') or '').strip()
            if not pathogen_name:
                errors.append(f"Row {i+1}: No pathogen name, skipping.")
                continue
            genus, species, strain = parse_pathogen_name(pathogen_name)
            pathogen, _ = Pathogen.objects.get_or_create(
                genus=genus, species=species, strain=strain
            )

            # 3. Resolve Phytochemical
            phyto_name = (exp.get('phytochemical_name') or '').strip()
            if not phyto_name:
                errors.append(f"Row {i+1}: No phytochemical name, skipping.")
                continue
            phytochemical = get_or_create_case_insensitive(
                Phytochemical, 'compound_name', phyto_name
            )

            # 3b. Auto-enrich phytochemical
            try:
                enrich_phytochemical(phytochemical)
            except Exception:
                pass  # Non-critical

            # 4. Resolve Antibiotic (with class)
            abx_name = (exp.get('antibiotic_name') or '').strip()
            if not abx_name:
                errors.append(f"Row {i+1}: No antibiotic name, skipping.")
                continue
            antibiotic = get_or_create_case_insensitive(
                Antibiotic, 'antibiotic_name', abx_name
            )

            # Set antibiotic class if provided and not already set
            abx_class_name = (exp.get('antibiotic_class') or '').strip()
            if abx_class_name and not antibiotic.antibiotic_class:
                abx_class, _ = AntibioticClass.objects.get_or_create(
                    class_name__iexact=abx_class_name,
                    defaults={'class_name': abx_class_name}
                )
                antibiotic.antibiotic_class = abx_class
                antibiotic.save()

            # 5. Plant source M2M
            plant_source = (exp.get('plant_source') or '').strip()
            if plant_source:
                plant, _ = Plant.objects.get_or_create(
                    scientific_name__iexact=plant_source,
                    defaults={'scientific_name': plant_source}
                )
                plant.phytochemicals.add(phytochemical)

            # 6. MIC values
            mic_phyto_alone = _safe_decimal(exp.get('mic_phyto_alone'))
            mic_abx_alone = _safe_decimal(exp.get('mic_abx_alone'))
            mic_phyto_in_combo = _safe_decimal(exp.get('mic_phyto_in_combo'))
            mic_abx_in_combo = _safe_decimal(exp.get('mic_abx_in_combo'))
            mic_units = (exp.get('mic_units') or '\u00b5g/mL').strip()
            # Normalize common variants
            if mic_units.lower() in ('ug/ml', 'µg/ml', 'ug/ml'):
                mic_units = '\u00b5g/mL'

            # 7. FIC index — use provided or auto-calculate
            fic_index = _safe_decimal(exp.get('fic_index'))
            if fic_index is None:
                fic_index = auto_calculate_fic(
                    mic_phyto_alone, mic_abx_alone,
                    mic_phyto_in_combo, mic_abx_in_combo
                )

            # 8. Interpretation — use provided or auto-derive
            interpretation = (exp.get('interpretation') or '').strip()
            valid_interpretations = ['Synergy', 'Additive', 'Indifference', 'Antagonism']
            if interpretation not in valid_interpretations:
                interpretation = auto_interpret_fic(fic_index)

            # 9. Assay method
            assay_method = (exp.get('assay_method') or '').strip()
            valid_methods = ['checkerboard', 'time_kill', 'disk_diffusion', 'broth_microdilution', 'other']
            if assay_method not in valid_methods:
                assay_method = 'checkerboard'

            # 10. Create the experiment
            SynergyExperiment.objects.create(
                phytochemical=phytochemical,
                antibiotic=antibiotic,
                pathogen=pathogen,
                source=source,
                mic_phyto_alone=mic_phyto_alone,
                mic_abx_alone=mic_abx_alone,
                mic_phyto_in_combo=mic_phyto_in_combo,
                mic_abx_in_combo=mic_abx_in_combo,
                mic_units=mic_units,
                fic_index=fic_index,
                interpretation=interpretation,
                assay_method=assay_method,
                moa_observed=(exp.get('moa_observed') or ''),
                notes=(exp.get('notes') or ''),
            )
            saved_count += 1

        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")
            logger.exception(f"Error saving extracted experiment row {i+1}")

    return saved_count, errors


@login_required
def extract_from_pdf(request):
    """AI-assisted PDF data extraction using Gemini API."""
    # Check API key configuration
    if not settings.GEMINI_API_KEY:
        return render(request, 'synergy_data/extract_pdf.html', {
            'api_error': 'AI extraction requires a Gemini API key. Set GEMINI_API_KEY in your environment.',
        })

    context = {}

    if request.method == 'POST':
        action = request.POST.get('action', 'extract')

        # ── SAVE ACTION: Save selected rows to database ──
        if action == 'save':
            experiments_json = request.POST.get('experiments_json', '[]')
            selected_rows = request.POST.getlist('selected_rows')

            try:
                all_experiments = json.loads(experiments_json)
            except json.JSONDecodeError:
                messages.error(request, "Could not parse experiment data. Please try extracting again.")
                return redirect('extract_pdf')

            # Filter only selected rows
            selected_indices = set()
            for idx in selected_rows:
                try:
                    selected_indices.add(int(idx))
                except (ValueError, TypeError):
                    pass

            if not selected_indices:
                messages.warning(request, "No rows were selected. Please select at least one row to save.")
                context['experiments'] = all_experiments
                context['experiments_json'] = experiments_json
                context['paper_metadata'] = all_experiments[0] if all_experiments else {}
                return render(request, 'synergy_data/extract_pdf.html', context)

            experiments_to_save = [
                exp for i, exp in enumerate(all_experiments) if i in selected_indices
            ]

            saved_count, errors = _save_extracted_experiments(experiments_to_save)

            doi = experiments_to_save[0].get('source_doi', 'unknown') if experiments_to_save else 'unknown'
            if saved_count > 0:
                messages.success(request, f"Saved {saved_count} experiment(s) from DOI: {doi}")
            if errors:
                for err in errors[:5]:  # Show at most 5 errors
                    messages.warning(request, err)
                if len(errors) > 5:
                    messages.warning(request, f"...and {len(errors) - 5} more error(s).")

            return redirect('extract_pdf')

        # ── EXTRACT ACTION: Upload PDF and extract data ──
        if action == 'extract':
            # Rate limiting: 1 request per 5 seconds
            cache_key = f'pdf_extract_{request.user.id}'
            last_request = cache.get(cache_key)
            if last_request and (time.time() - last_request) < 5:
                messages.warning(request, "Please wait a few seconds before extracting again.")
                return render(request, 'synergy_data/extract_pdf.html', context)
            cache.set(cache_key, time.time(), 30)

            pdf_file = request.FILES.get('pdf_file')
            if not pdf_file:
                messages.error(request, "Please select a PDF file to upload.")
                return render(request, 'synergy_data/extract_pdf.html', context)

            if not pdf_file.name.lower().endswith('.pdf'):
                messages.error(request, "Only PDF files are accepted.")
                return render(request, 'synergy_data/extract_pdf.html', context)

            # Limit file size (20 MB)
            if pdf_file.size > 20 * 1024 * 1024:
                messages.error(request, "File too large. Maximum size is 20 MB.")
                return render(request, 'synergy_data/extract_pdf.html', context)

            # Step 1: Extract text from PDF
            try:
                paper_text = _extract_text_from_pdf(pdf_file)
            except Exception as e:
                logger.exception("PDF text extraction failed")
                messages.error(
                    request,
                    "Could not extract text from this PDF. The file may be scanned/image-based."
                )
                return render(request, 'synergy_data/extract_pdf.html', context)

            if not paper_text or len(paper_text.strip()) < 100:
                messages.error(
                    request,
                    "Could not extract meaningful text from this PDF. The file may be scanned/image-based."
                )
                return render(request, 'synergy_data/extract_pdf.html', context)

            # Step 2: Send to Gemini
            try:
                experiments = _call_gemini_api(paper_text)
            except json.JSONDecodeError as e:
                messages.error(
                    request,
                    "Gemini returned invalid JSON. Please try again."
                )
                context['raw_response'] = str(e)
                return render(request, 'synergy_data/extract_pdf.html', context)
            except ValueError as e:
                messages.error(request, str(e))
                return render(request, 'synergy_data/extract_pdf.html', context)
            except Exception as e:
                logger.exception("Gemini API call failed")
                messages.error(request, f"AI extraction failed: {str(e)}")
                return render(request, 'synergy_data/extract_pdf.html', context)

            if not isinstance(experiments, list) or len(experiments) == 0:
                messages.warning(request, "No experiments were found in this paper.")
                return render(request, 'synergy_data/extract_pdf.html', context)

            # Step 3: Validate and annotate each row
            for i, exp in enumerate(experiments):
                # Flag rows with missing critical data
                exp['row_index'] = i
                exp['warnings'] = []

                if not exp.get('source_doi'):
                    exp['warnings'].append('Missing DOI')
                if not exp.get('phytochemical_name'):
                    exp['warnings'].append('Missing phytochemical')
                if not exp.get('antibiotic_name'):
                    exp['warnings'].append('Missing antibiotic')
                if not exp.get('pathogen_name'):
                    exp['warnings'].append('Missing pathogen')

                # Check MIC consistency
                mic_vals = [exp.get('mic_phyto_alone'), exp.get('mic_abx_alone'),
                            exp.get('mic_phyto_in_combo'), exp.get('mic_abx_in_combo')]
                has_some_mic = any(v is not None for v in mic_vals)
                has_all_mic = all(v is not None for v in mic_vals)
                if has_some_mic and not has_all_mic and not exp.get('fic_index'):
                    exp['warnings'].append('Incomplete MIC values & no FIC')

                # Auto-calculate FIC if possible for preview
                if not exp.get('fic_index') and has_all_mic:
                    try:
                        calc_fic = auto_calculate_fic(
                            Decimal(str(mic_vals[0])), Decimal(str(mic_vals[1])),
                            Decimal(str(mic_vals[2])), Decimal(str(mic_vals[3]))
                        )
                        if calc_fic:
                            exp['fic_index'] = float(round(calc_fic, 4))
                            exp['interpretation'] = auto_interpret_fic(calc_fic)
                            exp['warnings'].append('FIC auto-calculated')
                    except Exception:
                        pass

            context['experiments'] = experiments
            context['experiments_json'] = json.dumps(experiments, default=str)
            context['paper_metadata'] = experiments[0] if experiments else {}
            context['total_extracted'] = len(experiments)
            context['pdf_filename'] = pdf_file.name

    return render(request, 'synergy_data/extract_pdf.html', context)
