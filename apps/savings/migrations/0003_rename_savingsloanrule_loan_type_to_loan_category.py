from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('savings', '0002_savingstransaction_charge_description_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='savingsloanrule',
            old_name='loan_type',
            new_name='loan_category',
        ),
        migrations.AlterModelOptions(
            name='savingsloanrule',
            options={'ordering': ['loan_category', 'rule_type']},
        ),
        migrations.AlterUniqueTogether(
            name='savingsloanrule',
            unique_together={('loan_category', 'rule_type')},
        ),
    ]