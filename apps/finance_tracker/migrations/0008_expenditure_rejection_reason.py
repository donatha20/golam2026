from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance_tracker', '0005_income_approval_date_income_approved_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenditure',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
    ]
