# CRUD Permission Audit

Date: 2026-04-06
Scope: CRUD and state-changing endpoints across Django apps (`apps/*`).

## Legend

- Guard:
  - `auth-only` = `@login_required` or `LoginRequiredMixin` only
  - `role-guarded` = explicit role check (for example `request.user.is_admin`)
  - `workflow-guarded` = custom workflow role gate (for example `_deny_loan_officer`)
- Method guard:
  - `POST-only` = endpoint explicitly restricted to POST
  - `mixed` = GET+POST, mutation inside POST branch
  - `none` = no explicit HTTP method restriction decorator

## Per-Endpoint Permission Checklist

### accounts

| Endpoint | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `users/create/` | Create | role-guarded | mixed | `apps/accounts/views.py:135`, `apps/accounts/views.py:137` |
| `users/<id>/edit/` | Update | role-guarded | mixed | `apps/accounts/views.py:167`, `apps/accounts/views.py:169` |
| `users/<id>/toggle-status/` | Deactivate/Activate | role-guarded | POST-only | `apps/accounts/views.py:203`, `apps/accounts/views.py:205` |
| `branches/create/` | Create | role-guarded | mixed | `apps/accounts/views.py:245`, `apps/accounts/views.py:247` |

Status: Generally safe (explicit admin checks present).

### core (settings CRUD)

| Endpoint group | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `settings/holidays/*` | C/R/U/D | auth-only | mixed | `apps/core/views.py:731`, `apps/core/views.py:774`, `apps/core/views.py:799` |
| `settings/branches/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:821`, `apps/core/views.py:878`, `apps/core/views.py:910` |
| `settings/loan-categories/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:933`, `apps/core/views.py:988`, `apps/core/views.py:1019` |
| `settings/loan-sectors/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:1042`, `apps/core/views.py:1086`, `apps/core/views.py:1112` |
| `settings/working-modes/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:1174`, `apps/core/views.py:1223`, `apps/core/views.py:1260` |
| `settings/penalties/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:1135`, `apps/core/views.py:1311`, `apps/core/views.py:1339` |
| `settings/income-sources/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:1362`, `apps/core/views.py:1406`, `apps/core/views.py:1432` |
| `settings/expense-categories/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:1455`, `apps/core/views.py:1499`, `apps/core/views.py:1525` |
| `settings/asset-categories/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:1548`, `apps/core/views.py:1596`, `apps/core/views.py:1624` |
| `settings/bank-accounts/*` | C/R/U/Deactivate | auth-only | mixed | `apps/core/views.py:1647`, `apps/core/views.py:1696`, `apps/core/views.py:1724` |

Status: High risk. Broad write/delete privileges for any authenticated user.

### savings

| Endpoint | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `categories/create/` | Create | auth-only | mixed | `apps/savings/views.py:124` |
| `categories/<id>/edit/` | Update | auth-only | mixed | `apps/savings/views.py:154` |
| `categories/<id>/delete/` | Delete (hard) | auth-only | mixed | `apps/savings/views.py:183`, `apps/savings/views.py:190` |
| `charges/*` (bulk actions in list view) | Activate/Deactivate/Delete | auth-only | mixed | `apps/savings/views.py:338`, `apps/savings/views.py:383`, `apps/savings/views.py:388` |
| `charges/<id>/edit/` | Update | auth-only | mixed | `apps/savings/views.py:450` |
| `charges/<id>/delete/` | Delete (hard) | auth-only | mixed | `apps/savings/views.py:487`, `apps/savings/views.py:495` |
| `transactions/<id>/reverse/` | Reverse | auth-only | mixed | `apps/savings/views.py:717` |
| `set_withdraw_charges` view | Create | no explicit guard decorator | none | `apps/savings/views.py:261` |
| `view_withdraw_charges` view | Read | no explicit guard decorator | none | `apps/savings/views.py:417` |
| `view_accounts` view | Read | no explicit guard decorator | none | `apps/savings/views.py:519` |

Status: High risk. Several mutation endpoints are auth-only; some views have no decorator.

### payroll

| Endpoint group | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| Department/Position/Employee CBVs | C/R/U | auth-only (`LoginRequiredMixin`) | n/a | `apps/payroll/views.py:67`, `apps/payroll/views.py:78`, `apps/payroll/views.py:185`, `apps/payroll/views.py:196` |
| Employee deactivate/reactivate | State change | auth-only | POST-only | `apps/payroll/views.py:225`, `apps/payroll/views.py:243` |
| Payroll approvals | Approve/Reject | auth-only | POST-only | `apps/payroll/views.py:304`, `apps/payroll/views.py:506`, `apps/payroll/views.py:546`, `apps/payroll/views.py:615`, `apps/payroll/views.py:633` |

Status: Medium-high risk. Sensitive HR and approval actions have no explicit role check.

### finance_tracker

| Endpoint group | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| Add income/expenditure/shareholder/capital | Create | auth-only | mixed | `apps/finance_tracker/views.py:30`, `apps/finance_tracker/views.py:142`, `apps/finance_tracker/views.py:692`, `apps/finance_tracker/views.py:772` |
| Approve/reject income/expenditure/capital | Workflow update | workflow-guarded + auth-only | mixed | `apps/finance_tracker/views.py:23`, `apps/finance_tracker/views.py:322`, `apps/finance_tracker/views.py:353`, `apps/finance_tracker/views.py:386`, `apps/finance_tracker/views.py:417`, `apps/finance_tracker/views.py:939` |

Status: Moderate. Better than other apps due to `_deny_loan_officer`, but still no strict decorator-level role policy.

### repayments

| Endpoint | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `record/` | Create | auth-only | mixed | `apps/repayments/urls.py:14` |
| `reverse/<id>/` | Reverse | auth-only | mixed | `apps/repayments/views.py:826` |

Status: Medium risk. Reversal endpoint lacks explicit role/permission gate.

### loans

| Endpoint | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `add/`, `add-group/` | Create | auth-only | mixed | `apps/loans/urls.py:25`, `apps/loans/urls.py:26` |
| `approval/<id>/`, `rejection/<id>/` | Workflow update | auth-only | mixed | `apps/loans/urls.py:31`, `apps/loans/urls.py:32` |
| `write-off/<id>/` | State change | auth-only | mixed | `apps/loans/views.py:1029`, `apps/loans/urls.py:67` |
| `penalties/clear/` | Bulk state change | auth-only | none | `apps/loans/views.py:1017`, `apps/loans/urls.py:46` |

Status: High risk for state-changing actions without explicit role checks; `clear_penalties` appears callable without POST guard.

### borrowers

| Endpoint | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `register/` | Create | auth-only | mixed | `apps/borrowers/views.py:48` |
| `<id>/edit/` | Update | auth-only | mixed | `apps/borrowers/views.py:452` |
| Delete endpoint | Missing | n/a | n/a | `apps/borrowers/urls.py:1` |

Status: Missing D (delete/deactivate route) in URLs.

### assets

| Endpoint | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `assets/add/`, `collaterals/add/` | Create | auth-only | mixed | `apps/assets/urls.py:15`, `apps/assets/urls.py:21` |
| `assets/`, `assets/<id>/`, `collaterals/` | Read | auth-only | n/a | `apps/assets/urls.py:14`, `apps/assets/urls.py:16`, `apps/assets/urls.py:20` |
| Update/Delete routes | Missing/unclear | n/a | n/a | `apps/assets/urls.py:1` |

Status: Partial CRUD only.

### financial_statements

| Endpoint | CRUD/State | Guard | Method guard | Evidence |
|---|---|---|---|---|
| `periods/add/`, `classifications/add/` | Create | auth-only | mixed | `apps/financial_statements/urls.py:25`, `apps/financial_statements/urls.py:30` |
| `periods/<id>/close/` | State change | auth-only | mixed | `apps/financial_statements/urls.py:26` |
| Update/Delete endpoints | Missing/limited | n/a | n/a | `apps/financial_statements/urls.py:1` |

Status: Workflow/reporting oriented, not full entity CRUD.

## Prioritized Fix List (Missing/Unsafe CRUD)

### P0 (Immediate)

1. Add role enforcement to destructive endpoints in `core` and `savings`.
   - Affected: `apps/core/views.py:799`, `apps/core/views.py:910`, `apps/core/views.py:1019`, `apps/core/views.py:1112`, `apps/core/views.py:1260`, `apps/core/views.py:1339`, `apps/core/views.py:1432`, `apps/core/views.py:1525`, `apps/core/views.py:1624`, `apps/core/views.py:1724`, `apps/savings/views.py:183`, `apps/savings/views.py:487`, `apps/savings/views.py:338`.
2. Add POST-only enforcement to state-changing endpoints currently using GET+POST patterns.
   - Affected: most delete/reverse/approve routes above; especially `apps/loans/views.py:1017` (`clear_penalties`).
3. Protect or decorate unsecured views in savings.
   - Affected: `apps/savings/views.py:261`, `apps/savings/views.py:417`, `apps/savings/views.py:519`.

### P1 (High)

4. Enforce role checks on payroll approval and deactivation actions.
   - Affected: `apps/payroll/views.py:225`, `apps/payroll/views.py:243`, `apps/payroll/views.py:304`, `apps/payroll/views.py:506`, `apps/payroll/views.py:546`, `apps/payroll/views.py:615`, `apps/payroll/views.py:633`.
5. Enforce role checks on loan state transitions.
   - Affected: `apps/loans/views.py:1017`, `apps/loans/views.py:1029`, and approval/rejection handlers in loans app routes.
6. Enforce role checks on repayment reversal.
   - Affected: `apps/repayments/views.py:826`.

### P2 (Medium)

7. Fill missing CRUD surface where needed.
   - Borrowers: add delete/deactivate endpoint if business rules require it (`apps/borrowers/urls.py:1`).
   - Assets: add update/delete routes if intended (`apps/assets/urls.py:1`).
8. Standardize deletion strategy (soft delete vs hard delete) and document per model.
   - Hard deletes currently present in categories/charges/holiday flows.
9. Add explicit authorization policy abstraction.
   - Introduce shared decorators/mixins (example: `@admin_required`, `RoleRequiredMixin`) and apply consistently.
10. Add tests for unauthorized mutation attempts (403 or redirect expected).

## Suggested Fix Pattern

Use a shared role guard and method guard for mutating views:

- Add `@require_http_methods(["POST"])` to delete/reverse/approve actions.
- Add an authorization guard (`request.user.is_admin` or role enum check) before mutation.
- Return 403 for API-style endpoints and redirect with message for HTML endpoints.

