import uuid

from django.db import migrations, models
from django.utils import timezone


def populate_repayment_transaction_ids(apps, schema_editor):
    Repayment = apps.get_model('repayment', 'Repayment')
    for repayment in Repayment.objects.filter(transaction_id__isnull=True).iterator():
        repayment.transaction_id = (
            f'REPAY-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:12].upper()}'
        )
        repayment.save(update_fields=('transaction_id',))


class Migration(migrations.Migration):

    dependencies = [
        ('repayment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='repayment',
            name='transaction_id',
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=40,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(
            populate_repayment_transaction_ids,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='repayment',
            name='transaction_id',
            field=models.CharField(
                editable=False,
                max_length=40,
                unique=True,
            ),
        ),
    ]
