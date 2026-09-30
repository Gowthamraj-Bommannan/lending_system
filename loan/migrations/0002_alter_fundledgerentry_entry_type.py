from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loan', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fundledgerentry',
            name='entry_type',
            field=models.CharField(
                choices=[
                    ('OPENING_BALANCE', 'Opening balance'),
                    ('CONTRIBUTION_RECEIVED', 'Contribution received'),
                    ('CONTRIBUTION_CANCELLED', 'Contribution cancelled'),
                    ('LOAN_APPROVED', 'Loan approved'),
                    ('LOAN_REPAID', 'Loan principal repaid'),
                ],
                max_length=24,
            ),
        ),
    ]
