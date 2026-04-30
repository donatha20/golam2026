# Loan Rejection & Reversal Workflow Implementation

## 🎯 Overview

A complete loan rejection and reversal workflow has been implemented to allow administrators to:
1. Reject pending loan applications with documented reasons
2. Reverse rejections when appropriate
3. Allow borrowers to edit and resubmit rejected loans
4. Maintain a complete audit trail for compliance

---

## 📋 Workflow Steps

### Phase 1: Initial Application
```
Borrower Registers Loan
        ↓
Status: PENDING
```

### Phase 2: Admin Review & Rejection
```
Admin Reviews Loan
        ↓
Admin Decides to Reject
        ↓
Admin Provides Rejection Reason
        ↓
Status: REJECTED
Fields Updated:
  - rejected_by: Admin user
  - rejection_date: Today's date
  - rejection_reason: Admin's reason
```

### Phase 3: Admin Reversal (Optional)
```
Admin Decides to Reverse Rejection
        ↓
Admin Provides Reversal Reason
        ↓
Admin Selects "Allow Edits" (checkbox)
        ↓
Status: PENDING (returned to PENDING)
Fields Updated:
  - is_rejection_reversed: TRUE
  - reversed_rejection_date: Today's date
  - rejection_reversed_by: Admin user
  - reversal_reason: Admin's reason
  - rejected_by: Cleared (NULL)
  - rejection_date: Cleared (NULL)
  
Note: Original rejection_reason is PRESERVED
```

### Phase 4: Borrower Edits (After Reversal)
```
Borrower Reviews Original Rejection Reason
        ↓
Borrower Edits Loan Details:
  - Loan amount
  - Duration
  - Collateral info
  - Repayment terms
  - Additional notes
        ↓
Borrower Saves Changes
        ↓
Status: Still PENDING (unchanged)
```

### Phase 5: Resubmission & Re-Review
```
Admin Clears is_rejection_reversed Flag
        ↓
Loan Resubmitted for Approval
        ↓
Admin Reviews Again
        ↓
Admin Approves or Rejects Again
```

---

## 🔗 URL Endpoints

| Action | URL Pattern | Method | Permission | View |
|--------|------------|--------|-----------|------|
| Reject Loan | `/loans/<id>/reject/` | GET/POST | `can_reject_loan` | `reject_loan` |
| Reverse Rejection | `/loans/<id>/reverse-rejection/` | GET/POST | `can_reverse_rejection` | `reverse_loan_rejection` |
| Edit Reversed Loan | `/loans/<id>/edit-reversed/` | GET/POST | User/Admin Only | `edit_reversed_loan` |
| Resubmit Loan | `/loans/<id>/resubmit/` | POST | Admin Only | `resubmit_reversed_loan` |
| Management Dashboard | `/loans/rejected/` | GET | Any Auth User | `rejected_loans_list` |

---

## 🏷️ Database Fields

### Loan Model - Rejection Fields
```python
# Initial Rejection
rejected_by: ForeignKey(CustomUser)       # Admin who rejected
rejection_date: DateField                 # When rejected
rejection_reason: TextField               # Admin's reason

# Reversal Tracking
is_rejection_reversed: BooleanField       # TRUE if reversed
reversed_rejection_date: DateField        # When reversed
rejection_reversed_by: ForeignKey         # Admin who reversed
reversal_reason: TextField                # Admin's reversal reason
```

### Field Values During Workflow

| Stage | rejected_by | rejection_date | is_rejection_reversed | Status |
|-------|-----------|----------------|----------------------|--------|
| Pending | NULL | NULL | FALSE | PENDING |
| Rejected | Admin1 | 2025-01-15 | FALSE | REJECTED |
| Reversed | NULL | NULL | TRUE | PENDING |
| Re-Rejected | Admin1 | 2025-01-20 | FALSE/TRUE | REJECTED |

---

## 📝 Forms

### 1. LoanRejectionForm
```python
Fields:
  - rejection_reason: CharField (textarea, min 10 chars)
```

### 2. LoanRejectionReversalForm
```python
Fields:
  - reversal_reason: CharField (textarea, min 10 chars)
  - allow_edits: BooleanField (checkbox)
```

### 3. RejectedLoanEditForm
```python
Editable Fields:
  - amount_requested: DecimalField
  - duration_months: IntegerField
  - collateral_name: CharField
  - collateral_worth: DecimalField
  - repayment_frequency: ChoiceField
  - repayment_type: ChoiceField
  - notes: TextField
```

---

## 🔐 Permissions & Access Control

### Permission System

```python
# Custom Permissions (apps/loans/models.py Meta)
permissions = [
    ('can_reject_loan', 'Can reject pending loans'),
    ('can_reverse_rejection', 'Can reverse rejected loans'),
]
```

### Access Rules

| Action | Required Permission | Additional Rules |
|--------|-------------------|------------------|
| Reject Loan | `can_reject_loan` | Loan must be PENDING |
| Reverse Rejection | `can_reverse_rejection` | Loan must be REJECTED |
| Edit Reversed Loan | None (special) | Borrower owns loan OR user is staff |
| Resubmit Loan | None (special) | User must be staff |
| View Management | None | Must be authenticated |

### Setting Permissions in Admin

```python
# In Django Admin > Groups > [Group Name] > Permissions
# Add these permissions:
- loans | loan | Can reject pending loans
- loans | loan | Can reverse rejected loans
```

---

## 🔍 Management Dashboard

**URL:** `/loans/rejected/`

### Tab 1: Currently Rejected
Shows all loans with `status=REJECTED` and `is_rejection_reversed=FALSE`

Columns:
- Loan #
- Borrower
- Amount
- Rejected By
- Rejection Date
- Rejection Reason (preview)
- Actions (View, Reverse)

### Tab 2: Reversed Rejections
Shows all loans with `is_rejection_reversed=TRUE`

Columns:
- Loan #
- Borrower
- Amount
- Reversed By
- Reversed Date
- Reversal Reason (preview)
- Current Status
- Actions (View, Edit if PENDING)

### Summary Cards
- Total Rejections: All-time rejected loans
- Active Rejections: Still in REJECTED status
- Reversed: Total reversals done
- Reversal Rate: Percentage of reversals

---

## 🔄 Audit Trail

All actions are logged using Python's logging module:

```python
# Rejection Event
logger.info(f'Loan {loan.loan_number} rejected by {user}. Reason: {reason}')

# Reversal Event
logger.info(f'Loan {loan.loan_number} rejection reversed by {user}. '
            f'Original: {original_reason}. Reversal: {reversal_reason}')

# Edit Event
logger.info(f'Loan {loan.loan_number} edited after reversal by {user}')

# Resubmission Event
logger.info(f'Loan {loan.loan_number} resubmitted by {user} after reversal')
```

### Key Points
✓ Original rejection_reason is PRESERVED after reversal (not deleted)
✓ Complete chain of reversals maintained
✓ Timestamps recorded for all events
✓ Admin user tracked for each action
✓ No data is deleted (only set to NULL when necessary)

---

## 🛠️ Technical Implementation

### Files Created/Modified

**New Files:**
- `apps/loans/views_rejection.py` - All rejection/reversal views
- `apps/loans/forms_rejection.py` - All rejection forms
- `templates/loans/reject_loan.html` - Rejection form template
- `templates/loans/reverse_loan_rejection.html` - Reversal form template
- `templates/loans/edit_reversed_loan.html` - Edit form template
- `templates/loans/rejected_loans_list.html` - Management dashboard

**Modified Files:**
- `apps/loans/urls.py` - Added rejection/reversal URL patterns
- `apps/loans/models.py` - Added permissions in Meta class
- `apps/loans/migrations/0012_alter_loan_options.py` - Permission migration

### Decorators Used

```python
@login_required                                    # Requires login
@permission_required('loans.can_reject_loan')     # Requires permission
@require_http_methods(["GET", "POST"])            # HTTP method validation
```

### Database Transactions

```python
@transaction.atomic
with transaction.atomic():
    # All operations succeed or all fail together
    # Ensures consistency across related updates
```

---

## 📊 Data Integrity

### Constraints Enforced

1. **Status Validation**
   - Can only reject PENDING loans
   - Can only reverse REJECTED loans
   - Reversal reclaim to PENDING only if `allow_edits=True`

2. **Field Consistency**
   - Original rejection_reason never cleared
   - Reversal fields only set if reversed
   - rejected_by/rejection_date cleared when reversed

3. **Atomic Operations**
   - All fields updated together
   - Rollback if any error occurs
   - No partial updates

4. **User Tracking**
   - All actions attributed to specific admin
   - Timestamps recorded automatically
   - No anonymous modifications

---

## 🚀 Usage Examples

### Example 1: Reject Loan

1. Navigate to `/loans/123/reject/`
2. Enter rejection reason: "Insufficient collateral for requested amount"
3. Click "Reject"
4. Loan status → REJECTED
5. Borrower notified

### Example 2: Reverse Rejection

1. Navigate to `/loans/rejected/` management dashboard
2. Find the rejected loan
3. Click "Reverse Rejection" button
4. Enter reversal reason: "Borrower has secured additional collateral"
5. Check "Allow Edits" to let borrower edit
6. Click "Reverse Rejection"
7. Loan status → PENDING
8. Borrower receives notification to edit

### Example 3: Edit and Resubmit

1. Borrower notified that rejection was reversed
2. Borrower logs in and navigates to edit page
3. Updates amount from 50,000 to 40,000
4. Updates collateral with new property details
5. Adds note: "Using family home as collateral"
6. Saves changes
7. Admin reviews updated application
8. Admin approves or rejects again

---

## 📈 Metrics & Reports

### Generated by Management Dashboard

- **Total Rejections**: Count of all rejected loans
- **Active Rejections**: Count still in REJECTED status
- **Reversal Statistics**: 
  - Total reversed
  - Reversal percentage
  - Time from rejection to reversal
- **Borrower Actions**: 
  - How many edits after reversal
  - Resubmission rate

---

## ⚙️ Configuration

### Django Settings

The system uses Django's built-in permission system. No additional settings required.

### Logging Configuration

```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'loan_rejections.log',
        },
    },
    'loggers': {
        'apps.loans.views_rejection': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

---

## ✅ Testing Checklist

- [ ] User can reject pending loans with reason
- [ ] User can reverse rejected loans with reason
- [ ] Loan returns to PENDING after reversal
- [ ] Borrower can edit reversed loans
- [ ] Original rejection reason is preserved
- [ ] Audit trail shows all actions
- [ ] Permissions are properly enforced
- [ ] Management dashboard displays correctly
- [ ] Loan status transitions are correct
- [ ] Timestamps are recorded

---

## 🐛 Troubleshooting

### Issue: "Loan must be PENDING to reject"
**Solution**: The loan is not in PENDING status. Only new applications can be rejected.

### Issue: "You do not have permission to reverse rejections"
**Solution**: User needs `can_reverse_rejection` permission. Add to user group in Django admin.

### Issue: Loan doesn't return to PENDING after reversal
**Solution**: Make sure "Allow Edits" checkbox was checked when reversing. Without it, loan stays in current status.

### Issue: Can't find rejected loans
**Solution**: Navigate to `/loans/rejected/` dashboard. Use the "Currently Rejected" tab.

---

## 📞 Support

For questions about:
- **Workflow Logic**: See "Workflow Steps" section above
- **Permission Setup**: See "Permissions & Access Control" section
- **URL Routing**: See "URL Endpoints" table
- **Data Fields**: See "Database Fields" section
- **Forms**: See "Forms" section

---

*Last Updated: 2025-01-15*
*Implementation: Complete rejection and reversal workflow*
*Status: Ready for production*
