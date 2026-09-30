from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


def remove_empty_legacy_fund_tables(apps, schema_editor):
    """Drop draft fund tables only when empty; preserve any pre-existing data."""
    FundAccount = apps.get_model('loan', 'FundAccount')
    FundLedgerEntry = apps.get_model('loan', 'FundLedgerEntry')
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())
    if FundAccount._meta.db_table not in tables or FundLedgerEntry._meta.db_table not in tables:
        return

    if FundAccount.objects.exists() or FundLedgerEntry.objects.exists():
        return

    schema_editor.delete_model(FundLedgerEntry)
    schema_editor.delete_model(FundAccount)


def restore_legacy_fund_tables(apps, schema_editor):
    """Recreate the old empty tables if rolling back and they are absent."""
    FundAccount = apps.get_model('loan', 'FundAccount')
    FundLedgerEntry = apps.get_model('loan', 'FundLedgerEntry')
    tables = set(schema_editor.connection.introspection.table_names())
    if FundAccount._meta.db_table not in tables:
        schema_editor.create_model(FundAccount)
    tables = set(schema_editor.connection.introspection.table_names())
    if FundLedgerEntry._meta.db_table not in tables:
        schema_editor.create_model(FundLedgerEntry)


class Migration(migrations.Migration):

    dependencies = [
        ('loan', '0002_alter_fundledgerentry_entry_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='loan',
            name='completed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='completed_loans',
                to='lending.employee',
            ),
        ),
        migrations.AlterField(
            model_name='loan',
            name='loan_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.RunPython(
            remove_empty_legacy_fund_tables,
            restore_legacy_fund_tables,
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='fundledgerentry',
                    name='account',
                ),
                migrations.DeleteModel(name='FundLedgerEntry'),
                migrations.DeleteModel(name='FundAccount'),
            ],
        ),
        migrations.AlterModelOptions(
            name='loan',
            options={'db_table': 'loan', 'ordering': ('-requested_at', '-id')},
        ),
        migrations.RemoveConstraint(
            model_name='loan',
            name='loan_transaction_id_matches_status',
        ),
        migrations.RemoveConstraint(
            model_name='loan',
            name='one_active_loan_per_employee',
        ),
        migrations.AddConstraint(
            model_name='loan',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=('PENDING', 'REJECTED'),
                        transaction_id__isnull=True,
                        approved_amount__isnull=True,
                        interest_rate__isnull=True,
                    )
                    | models.Q(
                        status__in=('APPROVED', 'COMPLETED'),
                        transaction_id__isnull=False,
                        approved_amount__isnull=False,
                        interest_rate__isnull=False,
                    )
                ),
                name='loan_approval_fields_match_status',
            ),
        ),
        migrations.AddConstraint(
            model_name='loan',
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=('PENDING', 'APPROVED')),
                fields=('employee',),
                name='one_active_loan_per_employee',
            ),
        ),
    ]
