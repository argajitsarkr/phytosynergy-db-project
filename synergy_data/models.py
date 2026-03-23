from django.db import models

# This table holds the controlled vocabulary for antibiotic classes.
class AntibioticClass(models.Model):
    class_name = models.CharField(max_length=100, unique=True, help_text="e.g., Beta-lactam, Aminoglycoside")
    description = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = "Antibiotic Class"
        verbose_name_plural = "Antibiotic Classes"

    def __str__(self):
        return self.class_name

# Table for storing phytochemical information.
class Phytochemical(models.Model):
    compound_name = models.CharField(max_length=255, unique=True)
    pubchem_cid = models.IntegerField(unique=True, null=True, blank=True, verbose_name="PubChem CID")
    canonical_smiles = models.TextField(blank=True, null=True, verbose_name="Canonical SMILES")
    inchi_key = models.CharField(max_length=27, unique=True, null=True, blank=True, verbose_name="InChI Key")
    molecular_weight = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Lipinski / Physicochemical properties (auto-fetched from PubChem)
    molecular_formula = models.CharField(max_length=100, null=True, blank=True, verbose_name="Molecular Formula")
    xlogp = models.FloatField(null=True, blank=True, verbose_name="XLogP")
    hbd = models.IntegerField(null=True, blank=True, verbose_name="H-Bond Donors")
    hba = models.IntegerField(null=True, blank=True, verbose_name="H-Bond Acceptors")
    tpsa = models.FloatField(null=True, blank=True, verbose_name="TPSA (Å²)")
    rotatable_bonds = models.IntegerField(null=True, blank=True, verbose_name="Rotatable Bonds")

    # RDKit-computed physicochemical properties
    logp = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True, help_text="Partition coefficient (Wildman-Crippen LogP)")
    num_rings = models.IntegerField(blank=True, null=True, help_text="Number of rings")
    heavy_atom_count = models.IntegerField(blank=True, null=True, help_text="Number of heavy (non-hydrogen) atoms")

    # Drug-likeness flags
    lipinski_violations = models.IntegerField(blank=True, null=True, help_text="Number of Lipinski Rule of 5 violations")
    is_drug_like = models.BooleanField(default=False, help_text="Passes Lipinski RO5 with ≤1 violation")

    # Chemical Taxonomy (auto-fetched from ClassyFire)
    chemical_superclass = models.CharField(max_length=200, null=True, blank=True, verbose_name="Chemical Superclass")
    chemical_class = models.CharField(max_length=200, null=True, blank=True, verbose_name="Chemical Class")
    chemical_subclass = models.CharField(max_length=200, null=True, blank=True, verbose_name="Chemical Subclass")

    @property
    def passes_lipinski(self):
        """Check Lipinski's Rule of Five: MW < 500, LogP < 5, HBD ≤ 5, HBA ≤ 10."""
        if any(v is None for v in [self.molecular_weight, self.xlogp, self.hbd, self.hba]):
            return None  # Cannot determine
        violations = 0
        if self.molecular_weight and float(self.molecular_weight) > 500:
            violations += 1
        if self.xlogp is not None and self.xlogp > 5:
            violations += 1
        if self.hbd is not None and self.hbd > 5:
            violations += 1
        if self.hba is not None and self.hba > 10:
            violations += 1
        return violations <= 1  # Passes if at most 1 violation

    def __str__(self):
        return self.compound_name

# Table for storing antibiotic information.
class Antibiotic(models.Model):
    antibiotic_name = models.CharField(max_length=255, unique=True)
    drugbank_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="DrugBank ID")
    antibiotic_class = models.ForeignKey(AntibioticClass, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.antibiotic_name

# Table for storing pathogen information.
class Pathogen(models.Model):
    genus = models.CharField(max_length=100)
    species = models.CharField(max_length=100)
    strain = models.CharField(max_length=100, blank=True, null=True)
    gram_stain = models.CharField(max_length=20, blank=True, null=True, help_text="e.g., Gram-positive, Gram-negative")

    class Meta:
        unique_together = ('genus', 'species', 'strain') # Ensures we don't enter the same strain twice

    def save(self, *args, **kwargs):
        if self.strain == '':
            self.strain = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.genus} {self.species} {self.strain or ''}".strip()

# Table for storing source publication information.
class Source(models.Model):
    doi = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="DOI")
    pmid = models.IntegerField(unique=True, null=True, blank=True, verbose_name="PMID")
    publication_year = models.IntegerField(null=True, blank=True)
    article_title = models.TextField(blank=True, null=True)
    journal = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.doi or self.article_title or f"Source ID: {self.id}"

# This is the main "fact" table connecting all other data.
class SynergyExperiment(models.Model):
    # Defines the controlled vocabulary for interpretation using Django's standard choices class
    class InterpretationChoices(models.TextChoices):
        SYNERGY = 'Synergy', 'Synergy (FIC ≤ 0.5)'
        ADDITIVE = 'Additive', 'Additive (0.5 < FIC ≤ 1.0)'
        INDIFFERENCE = 'Indifference', 'Indifference (1.0 < FIC ≤ 4.0)'
        ANTAGONISM = 'Antagonism', 'Antagonism (FIC > 4.0)'

    # Foreign Keys linking to our other tables
    phytochemical = models.ForeignKey(Phytochemical, on_delete=models.CASCADE)
    antibiotic = models.ForeignKey(Antibiotic, on_delete=models.CASCADE)
    pathogen = models.ForeignKey(Pathogen, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    # MIC values for compounds tested alone
    mic_phyto_alone = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MIC of Phyto Alone")
    mic_abx_alone = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MIC of Antibiotic Alone")
    
    # MIC values for compounds tested in combination
    mic_phyto_in_combo = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MIC of Phyto in Combination")
    mic_abx_in_combo = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MIC of Antibiotic in Combination")
    
    mic_units = models.CharField(max_length=20, default='µg/mL', verbose_name="MIC Units")
    
    # Synergy metrics
    fic_index = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="FIC Index")
    interpretation = models.CharField(max_length=20, choices=InterpretationChoices.choices, blank=True, null=True)
    
    # Experimental method
    assay_method = models.CharField(
        max_length=50,
        choices=[
            ('checkerboard', 'Checkerboard'),
            ('time_kill', 'Time-Kill'),
            ('disk_diffusion', 'Disk Diffusion'),
            ('broth_microdilution', 'Broth Microdilution'),
            ('other', 'Other'),
        ],
        default='checkerboard',
        blank=True, null=True,
        help_text="Experimental method used to determine synergy"
    )

    # Other data
    moa_observed = models.TextField(blank=True, null=True, verbose_name="Observed Mechanism of Action")
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.phytochemical} + {self.antibiotic} vs {self.pathogen}"
    
class Plant(models.Model):
    scientific_name = models.CharField(max_length=255, unique=True)  # e.g., "Curcuma longa"
    common_name = models.CharField(max_length=255, blank=True, null=True)  # e.g., "Turmeric"
    family = models.CharField(max_length=100, blank=True, null=True)  # e.g., "Zingiberaceae"
    phytochemicals = models.ManyToManyField('Phytochemical', blank=True, related_name='source_plants')

    def __str__(self):
        return self.scientific_name

    class Meta:
        verbose_name = "Plant"
        verbose_name_plural = "Plants"


    # Model to store a single view count for the entire site.
class SiteViewCounter(models.Model):
    count = models.PositiveIntegerField(default=0, help_text="The total number of page views for the site.")

    def __str__(self):
        return str(self.count)