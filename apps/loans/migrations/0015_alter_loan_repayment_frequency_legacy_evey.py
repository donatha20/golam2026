# Generated manually to keep repayment frequency choices aligned with runtime logic.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0014_add_activity_log"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loan",
            name="repayment_frequency",
            field=models.CharField(
                choices=[
                    ("daily", "Daily"),
                    ("evey_three_days", "Every 3 Days (Legacy)"),
                    ("every_three_days", "Every 3 Days"),
                    ("weekly", "Weekly"),
                    ("biweekly", "Bi-weekly"),
                    ("monthly", "Monthly"),
                    ("quarterly", "Quarterly"),
                    ("annually", "Annually"),
                ],
                default="monthly",
                max_length=20,
            ),
        ),
    ]
