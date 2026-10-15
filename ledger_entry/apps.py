from django.apps import AppConfig


class LedgerEntryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ledger_entry'
    verbose_name = 'Ledger Entries'
