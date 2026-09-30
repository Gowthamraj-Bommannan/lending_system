from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('lending', '0004_employee_date_of_birth_employeerole'),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS organization CASCADE;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]