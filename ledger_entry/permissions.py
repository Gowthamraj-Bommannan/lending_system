from employee.permissions import IsSuperAdmin


class IsSuperAdminLedgerReader(IsSuperAdmin):
    """Restrict ledger records and totals to the superuser."""