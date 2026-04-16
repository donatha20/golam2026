from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('borrowers', '0002_alter_borrower_branch_alter_borrowergroup_branch'),
    ]

    operations = [
        migrations.AddField(
            model_name='borrower',
            name='nickname',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
