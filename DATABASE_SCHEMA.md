# Database Schema Design - Microfinance Management System

## 🗄️ Core Entities Overview

### 1. User Management
```
CustomUser
├── id (Primary Key)
├── username
├── email
├── first_name
├── last_name
├── role (Admin/Loan Officer)
├── is_active
├── date_joined
├── branch_id (Foreign Key)
└── created_by (Foreign Key to User)
```

### 2. Borrower Management
```
Borrower
├── id (Primary Key)
├── borrower_id (Unique Reference Number)
├── first_name
├── last_name
├── gender
├── date_of_birth
├── marital_status
├── occupation
├── phone_number
├── email (Optional)
├── photo (ImageField)
├── id_type
├── id_number
├── id_issue_date
├── id_expiry_date
├── house_number
├── street
├── ward
├── district
├── region
├── next_of_kin_name
├── next_of_kin_relationship
├── next_of_kin_phone
├── next_of_kin_address
├── branch_id (Foreign Key)
├── registered_by (Foreign Key to User)
├── registration_date
├── status (Active/Suspended/Blacklisted)
├── created_at
└── updated_at
```

### 3. Loan Management
```
LoanType
├── id (Primary Key)
├── name
├── description
├── default_interest_rate
├── min_amount
├── max_amount
├── min_duration_months
├── max_duration_months
├── requires_savings
├── minimum_savings_percentage
└── is_active

Loan
├── id (Primary Key)
├── loan_number (Unique)
├── borrower_id (Foreign Key)
├── loan_type_id (Foreign Key)
├── amount_requested
├── amount_approved
├── interest_rate
├── duration_months
├── repayment_frequency (Daily/Weekly/Monthly)
├── application_date
├── approval_date
├── disbursement_date
├── status (Pending/Approved/Rejected/Disbursed/Completed/Defaulted)
├── approved_by (Foreign Key to User)
├── disbursed_by (Foreign Key to User)
├── notes
├── created_by (Foreign Key to User)
├── created_at
└── updated_at

LoanRepaymentSchedule
├── id (Primary Key)
├── loan_id (Foreign Key)
├── installment_number
├── due_date
├── principal_amount
├── interest_amount
├── total_amount
├── balance_after_payment
├── is_paid
├── paid_date
├── paid_amount
└── penalty_amount
```

### 4. Repayment Management
```
Payment
├── id (Primary Key)
├── payment_reference
├── loan_id (Foreign Key)
├── borrower_id (Foreign Key)
├── amount
├── payment_date
├── payment_method
├── collected_by (Foreign Key to User)
├── notes
├── created_at
└── updated_at

DailyCollection
├── id (Primary Key)
├── collection_date
├── collector_id (Foreign Key to User)
├── total_amount
├── total_payments
├── notes
├── created_at
└── updated_at
```

### 5. Savings Management
```
SavingsAccount
├── id (Primary Key)
├── account_number (Unique)
├── borrower_id (Foreign Key)
├── balance
├── minimum_balance
├── interest_rate
├── status (Active/Inactive/Closed)
├── opened_date
├── opened_by (Foreign Key to User)
├── created_at
└── updated_at

SavingsTransaction
├── id (Primary Key)
├── account_id (Foreign Key)
├── transaction_type (Deposit/Withdrawal)
├── amount
├── balance_after
├── transaction_date
├── processed_by (Foreign Key to User)
├── reference_number
├── notes
├── created_at
└── updated_at
```

### 6. Financial Records (Double-Entry Accounting)
```
Account
├── id (Primary Key)
├── account_code
├── account_name
├── account_type (Asset/Liability/Equity/Income/Expense)
├── parent_account_id (Foreign Key - Self)
├── is_active
├── created_at
└── updated_at

JournalEntry
├── id (Primary Key)
├── entry_number (Unique)
├── entry_date
├── description
├── reference_type (Loan/Payment/Savings/etc.)
├── reference_id
├── created_by (Foreign Key to User)
├── created_at
└── updated_at

JournalEntryLine
├── id (Primary Key)
├── journal_entry_id (Foreign Key)
├── account_id (Foreign Key)
├── debit_amount
├── credit_amount
├── description
└── created_at
```

### 7. Assets & Collateral
```
Asset
├── id (Primary Key)
├── asset_name
├── asset_type
├── purchase_date
├── purchase_value
├── current_value
├── depreciation_rate
├── status (Active/Disposed/Damaged)
├── location
├── notes
├── created_at
└── updated_at

Collateral
├── id (Primary Key)
├── loan_id (Foreign Key)
├── borrower_id (Foreign Key)
├── collateral_type
├── description
├── estimated_value
├── location
├── documents (FileField)
├── status (Active/Released/Liquidated)
├── created_at
└── updated_at
```

## 🔗 Key Relationships

1. **One-to-Many**: Borrower → Loans, Loans → Payments
2. **One-to-One**: Borrower → SavingsAccount
3. **Many-to-Many**: Loans → Collateral (through intermediate table)
4. **Hierarchical**: Account → Parent Account (self-referencing)

## 📊 Indexes for Performance
- Borrower: phone_number, borrower_id, status
- Loan: loan_number, status, borrower_id
- Payment: payment_date, loan_id
- JournalEntry: entry_date, reference_type
