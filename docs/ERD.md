# Employee Lending System — Runtime and Target ERD

This document separates what is **implemented in the configured PostgreSQL database today** from the **planned complete lending design**. Planned entities are design guidance only; they are not current Django models or physical tables. The diagrams are divided into application-owned data and Django framework/support tables so that framework tables are not mistaken for lending-domain tables.

## Application tables

The application's five domain tables are `employee`, `employee_role`, `contribution`, `loan`, and `repayment`. No organization, fund-account, ledger-entry, or interest-allocation table exists in the current physical database.

```mermaid
erDiagram
    EMPLOYEE ||--o{ EMPLOYEE_ROLE : assigned_roles
    EMPLOYEE ||--o{ CONTRIBUTION : owns
    EMPLOYEE o|--o{ CONTRIBUTION : cancels
    EMPLOYEE ||--o{ LOAN : requests
    EMPLOYEE o|--o{ LOAN : reviews
    EMPLOYEE o|--o{ LOAN : completed_by_after_repayment
    EMPLOYEE ||--o{ REPAYMENT : records
    LOAN ||--o{ REPAYMENT : receives

    EMPLOYEE {
        bigint id PK
        varchar password
        datetime last_login
        boolean is_superuser
        varchar email UK
        boolean is_staff
        boolean is_active
        datetime date_joined
        varchar employee_id UK
        varchar first_name
        varchar last_name
        date date_of_birth
        datetime created_at
        datetime updated_at
    }

    EMPLOYEE_ROLE {
        bigint id PK
        bigint employee_id FK
        varchar role
    }

    CONTRIBUTION {
        bigint id PK
        varchar transaction_id UK
        bigint employee_id FK
        decimal amount
        varchar status
        datetime contributed_at
        datetime cancelled_at
        bigint cancelled_by_id FK "nullable"
        varchar cancellation_reason
        varchar reference
        text remarks
        datetime created_at
        datetime updated_at
    }

    LOAN {
        bigint id PK
        uuid loan_id UK
        varchar transaction_id UK "nullable until approval"
        bigint employee_id FK
        decimal requested_amount
        varchar request_reason
        smallint repayment_term_months "1 to 12 months"
        decimal approved_amount "nullable until approval"
        decimal interest_rate "nullable until approval"
        varchar status
        datetime requested_at
        datetime reviewed_at
        bigint reviewed_by_id FK "nullable"
        varchar decision_reason
        datetime completed_at
        bigint completed_by_id FK "nullable"
        datetime created_at
        datetime updated_at
    }

    REPAYMENT {
        bigint id PK
        uuid repayment_id UK
        varchar transaction_id UK
        bigint loan_id FK
        bigint recorded_by_id FK
        smallint installment_number
        decimal principal_amount
        decimal interest_amount
        decimal total_amount
        datetime paid_at
        datetime created_at
    }
```

## Complete lending domain (current + planned apps)

The following is the target domain ERD across the current and future app boundaries. `EMPLOYEE`, `EMPLOYEE_ROLE`, `CONTRIBUTION`, `LOAN`, and `REPAYMENT` are implemented. `INTEREST_ALLOCATION` and `LEDGER_ENTRY` are proposed for future accounting work and must not be treated as deployed tables yet. The `_PLANNED` suffixes in this diagram label future entities; they are not literal Django table names.

```mermaid
erDiagram
    EMPLOYEE ||--o{ EMPLOYEE_ROLE : has
    EMPLOYEE ||--o{ CONTRIBUTION : contributes
    EMPLOYEE o|--o{ CONTRIBUTION : cancels
    EMPLOYEE ||--o{ LOAN : requests
    EMPLOYEE o|--o{ LOAN : reviews
    EMPLOYEE o|--o{ LOAN : completed_by_after_repayment
    LOAN ||--o{ REPAYMENT : repaid_by
    EMPLOYEE ||--o{ REPAYMENT : records_payment
    REPAYMENT ||--o{ INTEREST_ALLOCATION_PLANNED : allocates_interest
    EMPLOYEE ||--o{ INTEREST_ALLOCATION_PLANNED : receives_interest
    CONTRIBUTION o|--o{ LEDGER_ENTRY_PLANNED : source_contribution
    LOAN o|--o{ LEDGER_ENTRY_PLANNED : source_loan
    REPAYMENT o|--o{ LEDGER_ENTRY_PLANNED : source_repayment

    EMPLOYEE {
        bigint id PK
        varchar email UK
        varchar employee_id UK
        varchar first_name
        varchar last_name
        date date_of_birth
        boolean is_active
        boolean is_staff
        boolean is_superuser
    }

    EMPLOYEE_ROLE {
        bigint id PK
        bigint employee_id FK
        varchar role
    }

    CONTRIBUTION {
        bigint id PK
        varchar transaction_id UK
        bigint employee_id FK
        decimal amount
        varchar status
        datetime contributed_at
        datetime cancelled_at
        bigint cancelled_by_id FK
        varchar cancellation_reason
        varchar reference
        text remarks
    }

    LOAN {
        bigint id PK
        uuid loan_id UK
        varchar transaction_id UK "NULL until approval"
        bigint employee_id FK
        decimal requested_amount
        varchar request_reason
        smallint repayment_term_months
        decimal approved_amount
        decimal interest_rate
        varchar status "PENDING, APPROVED, REJECTED, COMPLETED"
        datetime requested_at
        datetime reviewed_at
        bigint reviewed_by_id FK
        varchar decision_reason
        datetime completed_at
        bigint completed_by_id FK
    }

    REPAYMENT {
        bigint id PK
        varchar transaction_id UK
        bigint loan_id FK
        bigint recorded_by_id FK
        smallint installment_number
        decimal principal_amount
        decimal interest_amount
        decimal total_amount
        datetime paid_at
        datetime created_at
    }

    INTEREST_ALLOCATION_PLANNED {
        bigint id PK
        bigint repayment_id FK
        bigint contributor_employee_id FK
        decimal contribution_basis
        decimal allocated_amount
        datetime created_at
    }

    LEDGER_ENTRY_PLANNED {
        bigint id PK
        varchar entry_type
        varchar direction
        decimal amount
        bigint contribution_id FK
        bigint loan_id FK
        bigint repayment_id FK
        datetime created_at
    }
```

### Future app boundaries

| App / area | Tables in the target design | Purpose / status |
| --- | --- | --- |
| `employee` | `employee`, `employee_role` | Implemented identity, authentication, and role assignment. |
| `contribution` | `contribution` | Implemented contributions and cancellation history. Contributions are active immediately. |
| `loan` | `loan` | Implemented requests and decisions. Fully repaid loans transition automatically to `COMPLETED`; no `DISBURSED` status. |
| `repayment` | `repayment` | Implemented borrower repayment records, principal balance validation, and automatic loan completion. |
| Future interest/accounting app | `interest_allocation`, `ledger_entry` | Proposed distribution audit and append-only fund transaction history; not implemented. |
| `common` | No database tables | Shared rules, exceptions, logging, and utilities. |

There is no `organization` table: this installation represents one organization and uses fixed rules in configuration. A separate `FundAccount` table is also not part of the current or required target diagram; the current available-funds value is derived. If a future ledger becomes the authoritative balance source, its posting and balance-reconciliation policy should be agreed before implementation.

## Django authorization bridge

`Employee` inherits Django's `PermissionsMixin`, so the database also contains `auth_group` and the `employee_groups` many-to-many bridge. These enable Django group-based permissions. Application roles (`admin`, `approver`, `developer`, and `tester`) are stored separately in `employee_role`; the current loan permissions check the `admin`/`approver` roles (and superuser status), not Django groups.

```mermaid
erDiagram
    EMPLOYEE ||--o{ EMPLOYEE_GROUPS : group_membership
    AUTH_GROUP ||--o{ EMPLOYEE_GROUPS : includes
    AUTH_GROUP ||--o{ AUTH_GROUP_PERMISSIONS : grants
    AUTH_PERMISSION ||--o{ AUTH_GROUP_PERMISSIONS : assigned
    DJANGO_CONTENT_TYPE ||--o{ AUTH_PERMISSION : describes

    EMPLOYEE_GROUPS {
        bigint id PK
        bigint employee_id FK
        int group_id FK
    }

    AUTH_GROUP {
        int id PK
        varchar name UK
    }

    AUTH_GROUP_PERMISSIONS {
        bigint id PK
        int group_id FK
        int permission_id FK
    }

    AUTH_PERMISSION {
        int id PK
        varchar name
        int content_type_id FK
        varchar codename
    }

    DJANGO_CONTENT_TYPE {
        int id PK
        varchar app_label
        varchar model
    }
```

> Django's standard `Employee.user_permissions` many-to-many model field has no corresponding physical join table in this database snapshot. Do not draw an employee-user-permission relationship as present unless its table is created/applied.

## Django operational tables (not lending entities)

These are present in the database for framework operation, but are not part of the lending domain ERD:

| Physical table | Purpose |
| --- | --- |
| `django_admin_log` | Django admin change history; its user FK points to `employee`. |
| `django_session` | Django session storage. |
| `django_migrations` | Records applied migrations, not application business data. |
| `django_content_type` | Framework registry of installed model types; referenced by `auth_permission` and admin log entries. |
| `auth_group`, `auth_group_permissions`, `auth_permission` | Django's optional group/permission framework. |
| `employee_groups` | Django `PermissionsMixin` group-membership join table. |

## Domain rules captured by the schema

- `employee_role` has a unique constraint on (`employee_id`, `role`).
- Contributions have `ACTIVE` and `CANCELLED` statuses; amounts must be positive. Application services enforce the configured contribution range and per-employee active-total cap.
- Loans have `PENDING`, `APPROVED`, `REJECTED`, and `COMPLETED` statuses. There is no `DISBURSED` status.
- A loan's `loan_id` identifies a request from creation. `transaction_id` is nullable until approval.
- A database constraint requires approved terms and a transaction ID for `APPROVED`/`COMPLETED` loans, while `PENDING`/`REJECTED` loans have no transaction ID or approved terms.
- A partial unique constraint permits at most one `PENDING` or `APPROVED` loan per employee.
- Each repayment stores principal, interest, and total; a database check enforces `total = principal + interest`.
- A borrower can repay only their own `APPROVED` loan, and principal cannot exceed remaining principal.
- Available funds are calculated by application logic as active contributions minus remaining approved-loan principal; principal repayment releases funds. No separate balance table is used.
- A loan becomes `COMPLETED` automatically when its approved principal has been fully repaid.
- Repayment records carry generated transaction IDs and a sequential installment number unique within each loan.
- Loan repayment term is 1–12 months; total flat interest is calculated for the selected term, and monthly cent-rounding is reconciled in the final installment.

## Historical migration notes

- The database has an old migration record under app label `organization`, but there is no physical organization table.
- Old applied loan draft migrations once defined fund tables. The current cleanup migration removes those tables when empty; they are not present in the current schema snapshot.
- Interest allocation and ledger tables have not been implemented.

The table inventory was checked from the configured PostgreSQL database using the project's virtual environment. Table state can differ between environments until their migrations are synchronized.
