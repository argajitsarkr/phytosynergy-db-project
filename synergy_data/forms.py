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


# Expected CSV columns for bulk import
BULK_CSV_COLUMNS = [
    'source_doi',
    'pathogen_full_name',
    'phytochemical_name',
    'antibiotic_name',
    'mic_phyto_alone',
    'mic_abx_alone',
    'mic_phyto_in_combo',
    'mic_abx_in_combo',
    'mic_units',
    'fic_index',
    'interpretation',
    'moa_observed',
]


class BulkCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV file matching the PhytoSynergyDB template.",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
        }),
    )

    def clean_csv_file(self):
        f = self.cleaned_data['csv_file']
        if not f.name.lower().endswith('.csv'):
            raise forms.ValidationError("Only .csv files are accepted.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 10 MB).")

        # Validate header row
        try:
            text = f.read().decode('utf-8-sig')
            f.seek(0)
            reader = csv.DictReader(io.StringIO(text))
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        except Exception:
            raise forms.ValidationError("Could not read the CSV file. Ensure it is UTF-8 encoded.")

        required = {'source_doi', 'pathogen_full_name', 'phytochemical_name', 'antibiotic_name'}
        missing = required - set(headers)
        if missing:
            raise forms.ValidationError(
                f"Missing required columns: {', '.join(sorted(missing))}. "
                "Download the template to see the expected format."
            )
        return f
