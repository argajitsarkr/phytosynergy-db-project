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
    def __str__(self):
        return self.class_name

# Table for storing phytochemical information.
class Phytochemical(models.Model):
    compound_name = models.CharField(max_length=255, unique=True)
    pubchem_cid = models.IntegerField(unique=True, null=True, blank=True, verbose_name="PubChem CID")
    canonical_smiles = models.TextField(blank=True, null=True, verbose_name="Canonical SMILES")
    inchi_key = models.CharField(max_length=27, unique=True, null=True, blank=True, verbose_name="InChI Key")
    molecular_weight = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

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
    
    # Other data
    moa_observed = models.TextField(blank=True, null=True, verbose_name="Observed Mechanism of Action")
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.phytochemical} + {self.antibiotic} vs {self.pathogen}"
    
    # Model to store a single view count for the entire site.
class SiteViewCounter(models.Model):
    count = models.PositiveIntegerField(default=0, help_text="The total number of page views for the site.")

    def __str__(self):
        return str(self.count)