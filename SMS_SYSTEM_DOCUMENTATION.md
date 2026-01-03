# SMS Management System Documentation

## Overview

The Golam Microfinance System includes a comprehensive SMS management module that enables automated and manual SMS communications with borrowers and customers.

## Features

### 🚀 Core SMS Functionality
- **Individual SMS**: Send SMS to specific phone numbers
- **Bulk SMS**: Send SMS to groups of borrowers (all, active, overdue)
- **Template Management**: Pre-defined SMS templates for common scenarios
- **SMS Logging**: Complete audit trail of all SMS communications
- **Provider Support**: Multiple SMS provider integrations

### 📊 SMS Dashboard
- Real-time SMS statistics and analytics
- Recent SMS activity monitoring
- Provider status and configuration
- Quick action buttons for common tasks

### 🔧 SMS Settings & Configuration
- Multiple provider support (Twilio, TextLocal, MSG91, Dummy)
- Environment-based configuration
- Test SMS functionality
- Provider switching capabilities

### 📋 SMS Templates
Pre-configured templates for:
- **Loan Approval**: Sent when loans are approved
- **Loan Disbursement**: Sent when loan amounts are disbursed
- **Payment Reminder**: Sent for upcoming payment due dates
- **Overdue Reminder**: Sent for overdue payments
- **Payment Confirmation**: Sent after successful payments
- **Savings Transaction**: Sent for savings account activities

## Technical Implementation

### SMS Service Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SMS Views     │────│   SMS Service   │────│  SMS Providers  │
│  (User Interface)│    │   (Core Logic)  │    │ (Twilio/etc.)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │    SMS Log      │
                       │   (Database)    │
                       └─────────────────┘
```

### SMS Provider Configuration

#### Twilio Configuration
```bash
SMS_ENABLED=True
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
```

#### TextLocal Configuration
```bash
SMS_ENABLED=True
SMS_PROVIDER=textlocal
TEXTLOCAL_API_KEY=your_api_key_here
TEXTLOCAL_SENDER=TXTLCL
```

#### MSG91 Configuration
```bash
SMS_ENABLED=True
SMS_PROVIDER=msg91
MSG91_AUTH_KEY=your_auth_key_here
MSG91_SENDER_ID=MSGIND
```

### Automatic SMS Integration

The system automatically sends SMS notifications for:

1. **Loan Approval** (`apps/loans/views.py`)
   - Triggered when a loan is approved
   - Uses `loan_approval.txt` template
   - Includes loan details and next steps

2. **Loan Disbursement** (`apps/loans/views.py`)
   - Triggered when loan amount is disbursed
   - Uses `loan_disbursement.txt` template
   - Includes disbursement details and first payment date

3. **Payment Confirmation** (`apps/repayments/views.py`)
   - Triggered when payment is recorded
   - Uses `payment_confirmation.txt` template
   - Includes payment details and remaining balance

### Management Commands

#### Send Payment Reminders
```bash
# Send reminders for payments due in 3 days
python manage.py send_payment_reminders

# Send reminders for payments due in 7 days
python manage.py send_payment_reminders --days-ahead 7

# Send overdue reminders only
python manage.py send_payment_reminders --overdue-only

# Dry run to see what would be sent
python manage.py send_payment_reminders --dry-run
```

## URL Structure

```
/sms/                           # SMS Dashboard
/sms/send/                      # Send Individual SMS
/sms/bulk/                      # Send Bulk SMS
/sms/logs/                      # View SMS Logs
/sms/templates/                 # Manage SMS Templates
/sms/settings/                  # SMS Configuration
/sms/test/                      # Test SMS (AJAX endpoint)
```

## Database Schema

### SMSLog Model
```python
class SMSLog(models.Model):
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20)
    provider = models.CharField(max_length=50)
    template_name = models.CharField(max_length=100, null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    provider_response = models.JSONField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
```

## Security Features

- **Input Validation**: Phone numbers and messages are validated
- **Rate Limiting**: Prevents SMS spam and abuse
- **Audit Logging**: Complete trail of all SMS activities
- **Provider Isolation**: SMS provider credentials are environment-based
- **Error Handling**: Graceful handling of provider failures

## Best Practices

### Message Content
- Keep messages under 160 characters when possible
- Always include organization name
- Use clear, professional language
- Include relevant reference numbers (loan numbers, payment IDs)

### Timing
- Send messages during business hours (9 AM - 6 PM)
- Respect time zones for different regions
- Avoid sending on weekends and holidays

### Technical
- Test thoroughly before bulk sending
- Monitor delivery rates and costs
- Use templates for consistency
- Implement proper error handling

## Monitoring & Analytics

### SMS Dashboard Metrics
- Total SMS sent (all time)
- SMS sent today/this week/this month
- Status breakdown (sent/failed/delivered)
- Template usage statistics
- Provider performance metrics

### SMS Logs
- Complete history of all SMS communications
- Filtering by status, template, phone number, date range
- Pagination for large datasets
- Export capabilities for reporting

## Integration Points

### Loan Management
- Automatic SMS on loan approval
- Automatic SMS on loan disbursement
- Integration with loan workflow

### Repayment Management
- Automatic SMS on payment confirmation
- Payment reminder scheduling
- Overdue notification system

### Borrower Management
- SMS integration with borrower profiles
- Bulk messaging to borrower groups
- Communication history tracking

## Troubleshooting

### Common Issues

1. **SMS Not Sending**
   - Check SMS_ENABLED setting
   - Verify provider credentials
   - Check provider account balance
   - Review error logs

2. **Template Not Found**
   - Ensure template files exist in templates/sms/
   - Check template name spelling
   - Verify template syntax

3. **Provider Errors**
   - Check provider API status
   - Verify account credentials
   - Check rate limits
   - Review provider documentation

### Error Handling
- All SMS operations include try/catch blocks
- Graceful degradation when SMS service is unavailable
- User-friendly error messages
- Detailed logging for debugging

## Future Enhancements

### Planned Features
- **SMS Scheduling**: Schedule SMS for future delivery
- **SMS Templates Editor**: Web-based template management
- **SMS Analytics**: Advanced reporting and analytics
- **Two-way SMS**: Handle incoming SMS responses
- **SMS Campaigns**: Marketing campaign management

### Integration Opportunities
- **WhatsApp Integration**: Extend to WhatsApp messaging
- **Email Integration**: Unified communication platform
- **Voice Calls**: Automated voice reminders
- **Push Notifications**: Mobile app notifications

## Support

For SMS system support:
- **Documentation**: Check this file and inline code comments
- **Configuration**: Review environment variables and settings
- **Testing**: Use the built-in test SMS functionality
- **Logs**: Check SMS logs for delivery status and errors

---

**SMS Management System** - Enabling effective communication in microfinance operations.
