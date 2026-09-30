from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loan', '0003_loan_runtime_schema'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='request_reason',
            field=models.CharField(
                default='Legacy loan request: reason not recorded.',
                max_length=1000,
            ),
            preserve_default=False,
        ),
    ]
