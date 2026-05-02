from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('synergy_data', '0004_phytochemical_heavy_atom_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteviewcounter',
            name='unique_visitors',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Total number of unique sessions seen.',
            ),
        ),
    ]
