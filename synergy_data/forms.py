import csv
import io

from django import forms
from .models import SynergyExperiment


class SynergyEntryForm(forms.Form):
    """
    A plain Form (not ModelForm) because we need get_or_create logic
    for the FK fields before saving the SynergyExperiment.
    Mirrors the Google Sheets columns used for data curation.
    """

    # --- Source ---
    source_doi = forms.CharField(
        max_length=255,
        required=True,
        label="Source DOI",
        help_text="e.g., 10.1038/srep23347",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10.1038/srep23347',
        }),
    )

    publication_year = forms.IntegerField(
        required=False,
        label="Publication Year",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 2024',
            'min': '1900',
            'max': '2099',
        }),
    )

    article_title = forms.CharField(
        max_length=500,
        required=False,
        label="Article Title",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Synergistic activity of flavonoids...',
        }),
    )

    journal = forms.CharField(
        max_length=255,
        required=False,
        label="Journal",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Journal of Antimicrobial Chemotherapy',
        }),
    )

    # --- Entity name fields (resolved to FKs in the view) ---
    pathogen_full_name = forms.CharField(
        max_length=300,
        required=True,
        label="Pathogen Full Name",
        help_text='Format: "Genus species Strain" e.g., "Pseudomonas aeruginosa MTCC 2488"',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pseudomonas aeruginosa MTCC 2488',
        }),
    )

    phytochemical_name = forms.CharField(
        max_length=255,
        required=True,
        label="Phytochemical Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Vitexin',
        }),
    )

    antibiotic_name = forms.CharField(
        max_length=255,
        required=True,
        label="Antibiotic Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Azithromycin',
        }),
    )

    antibiotic_class = forms.CharField(
        max_length=100,
        required=False,
        label="Antibiotic Class",
        help_text="e.g., Fluoroquinolone, Beta-lactam (optional)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Fluoroquinolone',
        }),
    )

    plant_source = forms.CharField(
        max_length=255,
        required=False,
        label="Plant Source",
        help_text="Scientific name of the source plant, e.g., Berberis vulgaris (optional)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Berberis vulgaris',
        }),
    )

    gram_stain = forms.ChoiceField(
        choices=[
            ('', '--- Auto-derive from genus ---'),
            ('Gram-positive', 'Gram-positive'),
            ('Gram-negative', 'Gram-negative'),
        ],
        required=False,
        label="Gram Stain",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    # --- MIC values (all optional -- papers often have partial data) ---
    mic_phyto_alone = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label="MIC Phyto Alone",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.0001',
            'placeholder': 'e.g., 260',
        }),
    )

    mic_abx_alone = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label="MIC Antibiotic Alone",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.0001',
            'placeholder': 'e.g., 55',
        }),
    )

    mic_phyto_in_combo = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label="MIC Phyto in Combo",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.0001',
            'placeholder': 'e.g., 110',
        }),
    )

    mic_abx_in_combo = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label="MIC Antibiotic in Combo",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.0001',
            'placeholder': 'e.g., 13.75',
        }),
    )

    mic_units = forms.CharField(
        max_length=20,
        required=False,
        initial='\u00b5g/mL',
        label="MIC Units",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '\u00b5g/mL',
        }),
    )

    # --- Synergy metrics ---
    fic_index = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        label="FIC Index",
        help_text="Leave blank to auto-calculate from MIC values",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.0001',
            'placeholder': 'Auto-calculated if blank',
        }),
    )

    interpretation = forms.ChoiceField(
        choices=[('', '--- Auto-derive from FIC ---')]
        + list(SynergyExperiment.InterpretationChoices.choices),
        required=False,
        label="Interpretation",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    assay_method = forms.ChoiceField(
        choices=[
            ('checkerboard', 'Checkerboard'),
            ('time_kill', 'Time-Kill'),
            ('disk_diffusion', 'Disk Diffusion'),
            ('broth_microdilution', 'Broth Microdilution'),
            ('other', 'Other'),
        ],
        required=False,
        initial='checkerboard',
        label="Assay Method",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    # --- Additional info ---
    moa_observed = forms.CharField(
        required=False,
        label="Observed Mechanism of Action",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'e.g., Membrane disruption, Efflux pump inhibition...',
        }),
    )

    notes = forms.CharField(
        required=False,
        label="Notes",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any additional notes...',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        mic_fields = [
            cleaned_data.get('mic_phyto_alone'),
            cleaned_data.get('mic_abx_alone'),
            cleaned_data.get('mic_phyto_in_combo'),
            cleaned_data.get('mic_abx_in_combo'),
        ]
        has_all_mic = all(v is not None for v in mic_fields)
        has_fic = cleaned_data.get('fic_index') is not None

        if not has_all_mic and not has_fic:
            raise forms.ValidationError(
                "Each entry must have either all 4 MIC values (for auto-FIC calculation) "
                "or a manually entered FIC index. Entries without quantitative synergy "
                "data (e.g., disk diffusion only) cannot be added."
            )
        return cleaned_data


# Canonical column order shown in the downloaded template.
# Pathogen is split into genus / species / strain to prevent ambiguous
# free-text entries (e.g. the "S. aureus" -> genus "S." bug). gram_stain and
# pmid are new optional columns.
BULK_CSV_COLUMNS = [
    'source_doi',
    'pmid',
    'publication_year',
    'article_title',
    'journal',
    'pathogen_genus',
    'pathogen_species',
    'pathogen_strain',
    'gram_stain',
    'phytochemical_name',
    'plant_source',
    'antibiotic_name',
    'antibiotic_class',
    'mic_phyto_alone',
    'mic_abx_alone',
    'mic_phyto_in_combo',
    'mic_abx_in_combo',
    'mic_units',
    'fic_index',
    'interpretation',
    'assay_method',
    'moa_observed',
    'notes',
]


# Maps whatever a student typed as a header (lower-cased, whitespace-stripped)
# to the canonical internal field name used by the import pipeline. Handles the
# common variations seen in real collection spreadsheets.
COLUMN_MAP = {
    # Source / publication metadata
    'source_doi': 'source_doi',
    'doi': 'source_doi',
    'pmid': 'pmid',
    'pubmed': 'pmid',
    'pubmed_id': 'pmid',
    'publication_year': 'publication_year',
    'year': 'publication_year',
    'article_title': 'article_title',
    'title': 'article_title',
    'paper_title': 'article_title',
    'journal': 'journal',
    'journal_name': 'journal',

    # Pathogen (preferred: split genus / species / strain)
    'pathogen_genus': 'pathogen_genus',
    'genus': 'pathogen_genus',
    'pathogen_species': 'pathogen_species',
    'species': 'pathogen_species',
    'pathogen_strain': 'pathogen_strain',
    'strain': 'pathogen_strain',
    'gram_stain': 'gram_stain',
    'gram': 'gram_stain',
    'gramstain': 'gram_stain',
    # Legacy single-column pathogen (still accepted; composed if parts absent)
    'pathogen_full_name': 'pathogen_full_name',
    'pathogen_name': 'pathogen_full_name',
    'pathogen': 'pathogen_full_name',
    'organism': 'pathogen_full_name',
    'bacteria': 'pathogen_full_name',

    # Phytochemical
    'phytochemical_name': 'phytochemical_name',
    'phytochemical': 'phytochemical_name',
    'compound': 'phytochemical_name',
    'compound_name': 'phytochemical_name',
    'natural_product': 'phytochemical_name',
    'plant_source': 'plant_source',
    'plant': 'plant_source',
    'source_plant': 'plant_source',

    # Antibiotic
    'antibiotic_name': 'antibiotic_name',
    'antibiotic': 'antibiotic_name',
    'drug': 'antibiotic_name',
    'antibiotic_class': 'antibiotic_class',
    'drug_class': 'antibiotic_class',

    # MIC values
    'mic_phyto_alone': 'mic_phyto_alone',
    'mic_phytochemical_alone': 'mic_phyto_alone',
    'mic_compound_alone': 'mic_phyto_alone',
    'mic_abx_alone': 'mic_abx_alone',
    'mic_antibiotic_alone': 'mic_abx_alone',
    'mic_drug_alone': 'mic_abx_alone',
    'mic_phyto_in_combo': 'mic_phyto_in_combo',
    'mic_phytochemical_in_combo': 'mic_phyto_in_combo',
    'mic_phyto_combo': 'mic_phyto_in_combo',
    'mic_compound_combo': 'mic_phyto_in_combo',
    'mic_abx_in_combo': 'mic_abx_in_combo',
    'mic_antibiotic_in_combo': 'mic_abx_in_combo',
    'mic_abx_combo': 'mic_abx_in_combo',
    'mic_drug_combo': 'mic_abx_in_combo',
    'mic_units': 'mic_units',
    'units': 'mic_units',
    'concentration_units': 'mic_units',

    # Synergy metrics
    'fic_index': 'fic_index',
    'fic': 'fic_index',
    'fici': 'fic_index',
    'interpretation': 'interpretation',
    'synergy_interpretation': 'interpretation',
    'result': 'interpretation',

    # Method & notes
    'assay_method': 'assay_method',
    'method': 'assay_method',
    'moa_observed': 'moa_observed',
    'mechanism': 'moa_observed',
    'mechanism_of_action': 'moa_observed',
    'moa': 'moa_observed',
    'notes': 'notes',
    'comments': 'notes',
    'remarks': 'notes',
}


def _canonical_header(raw_header):
    """Normalize one raw header cell to its canonical internal name.

    Returns the canonical name if recognised, otherwise an empty string so
    unknown columns are silently ignored rather than crashing the import.
    """
    if raw_header is None:
        return ''
    h = (
        str(raw_header)
        .replace('\t', '')
        .replace('\r', '')
        .replace('\xa0', ' ')
        .strip()
        .lower()
        .replace(' ', '_')
    )
    return COLUMN_MAP.get(h, '')


class BulkCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Data file (.csv or .xlsx)",
        help_text="Upload a CSV or Excel (.xlsx) file matching the PhytoSynergyDB template.",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx',
        }),
    )

    def clean_csv_file(self):
        f = self.cleaned_data['csv_file']
        name = f.name.lower()
        if not (name.endswith('.csv') or name.endswith('.xlsx')):
            raise forms.ValidationError("Only .csv or .xlsx files are accepted.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 10 MB).")

        # Read the header row from either format to validate required columns.
        try:
            if name.endswith('.xlsx'):
                import openpyxl  # local import - only needed on xlsx path
                f.seek(0)
                wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
                ws = wb.active
                header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
                headers = [_canonical_header(h) for h in header_row]
                f.seek(0)
            else:
                text = f.read().decode('utf-8-sig')
                f.seek(0)
                reader = csv.DictReader(io.StringIO(text))
                headers = [_canonical_header(h) for h in (reader.fieldnames or [])]
        except forms.ValidationError:
            raise
        except Exception as e:
            raise forms.ValidationError(
                f"Could not read the uploaded file: {e}. "
                "Ensure CSV files are UTF-8 encoded and XLSX files are valid Excel workbooks."
            )

        present = set(headers)
        required = {'source_doi', 'phytochemical_name', 'antibiotic_name'}
        missing = required - present
        # Pathogen may be given as split genus (preferred) or the legacy
        # single full-name column.
        if 'pathogen_genus' not in present and 'pathogen_full_name' not in present:
            missing.add('pathogen_genus')
        if missing:
            raise forms.ValidationError(
                f"Missing required columns: {', '.join(sorted(missing))}. "
                "Accepted aliases include 'doi', 'genus'/'pathogen', 'compound', "
                "'antibiotic'. Download the template to see the expected format."
            )
        return f
