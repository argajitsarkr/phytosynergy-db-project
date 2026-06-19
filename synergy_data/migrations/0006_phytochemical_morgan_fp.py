from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('synergy_data', '0005_siteviewcounter_unique_visitors'),
    ]

    operations = [
        migrations.AddField(
            model_name='phytochemical',
            name='morgan_fp',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='2048-bit ECFP4 (Morgan radius 2) fingerprint bit string, for similarity search',
                verbose_name='Morgan/ECFP4 Fingerprint',
            ),
        ),
    ]
