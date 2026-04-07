"""
SMS Service for Loan Management System
Supports multiple SMS providers: Twilio, TextLocal, MSG91, etc.
"""
import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal
from typing import Optional, Dict, Any
import requests
import json

logger = logging.getLogger(__name__)


class SMSService:
    """Main SMS service class that handles different providers."""
    
    def __init__(self):
        self.provider = getattr(settings, 'SMS_PROVIDER', 'twilio').lower()
        self.enabled = getattr(settings, 'SMS_ENABLED', False)
        
        if self.provider == 'twilio':
            self.service = TwilioSMSService()
        elif self.provider == 'textlocal':
            self.service = TextLocalSMSService()
        elif self.provider == 'msg91':
            self.service = MSG91SMSService()
        else:
            self.service = DummySMSService()
    
    def send_sms(self, phone_number: str, message: str, template_name: str = None) -> Dict[str, Any]:
        """Send SMS message."""
        if not self.enabled:
            logger.info(f"SMS disabled. Would send to {phone_number}: {message}")
            return {'success': True, 'message': 'SMS disabled', 'provider': 'disabled'}
        
        try:
            # Clean phone number
            phone_number = self._clean_phone_number(phone_number)
            
            # Send via provider
            result = self.service.send_message(phone_number, message)
            
            # Log the SMS
            self._log_sms(phone_number, message, template_name, result)
            
            return result
            
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_loan_reminder(self, loan, days_overdue: int = 0):
        """Send loan payment reminder SMS."""
        borrower = loan.borrower
        
        if not borrower.phone_number:
            return {'success': False, 'error': 'No phone number available'}
        
        context = {
            'borrower_name': borrower.get_full_name(),
            'loan_number': loan.loan_number,
            'outstanding_amount': loan.outstanding_balance,
            'days_overdue': days_overdue,
            'next_due_date': loan.next_due_date,
            'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Microfinance'),
        }
        
        if days_overdue > 0:
            template = 'sms/overdue_reminder.txt'
        else:
            template = 'sms/payment_reminder.txt'
        
        message = render_to_string(template, context).strip()
        
        return self.send_sms(
            borrower.phone_number, 
            message, 
            template_name='loan_reminder'
        )
    
    def send_payment_confirmation(self, payment):
        """Send payment confirmation SMS."""
        borrower = payment.loan.borrower
        
        if not borrower.phone_number:
            return {'success': False, 'error': 'No phone number available'}
        
        context = {
            'borrower_name': borrower.get_full_name(),
            'amount': payment.amount,
            'loan_number': payment.loan.loan_number,
            'payment_date': payment.payment_date,
            'remaining_balance': payment.loan.outstanding_balance,
            'payment_reference': payment.payment_reference,
            'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Microfinance'),
        }
        
        message = render_to_string('sms/payment_confirmation.txt', context).strip()
        
        return self.send_sms(
            borrower.phone_number, 
            message, 
            template_name='payment_confirmation'
        )
    
    def send_loan_approval(self, loan):
        """Send loan approval SMS."""
        borrower = loan.borrower
        
        if not borrower.phone_number:
            return {'success': False, 'error': 'No phone number available'}
        
        context = {
            'borrower_name': borrower.get_full_name(),
            'loan_number': loan.loan_number,
            'loan_amount': loan.principal_amount,
            'interest_rate': loan.interest_rate,
            'tenure': loan.tenure_months,
            'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Microfinance'),
        }
        
        message = render_to_string('sms/loan_approval.txt', context).strip()
        
        return self.send_sms(
            borrower.phone_number, 
            message, 
            template_name='loan_approval'
        )
    
    def send_loan_rejection(self, loan):
        """Send loan rejection SMS."""
        borrower = loan.borrower
        
        if not borrower.phone_number:
            return {'success': False, 'error': 'No phone number available'}
        
        context = {
            'borrower_name': borrower.get_full_name(),
            'loan_number': loan.loan_number,
            'rejection_reason': loan.rejection_reason,
            'contact_info': getattr(settings, 'ORGANIZATION_CONTACT', 'Please contact us for more information'),
            'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Microfinance'),
        }
        
        message = render_to_string('sms/loan_rejection.txt', context).strip()
        
        return self.send_sms(
            borrower.phone_number, 
            message, 
            template_name='loan_rejection'
        )
    
    def send_loan_disbursement(self, loan):
        """Send loan disbursement SMS."""
        borrower = loan.borrower
        
        if not borrower.phone_number:
            return {'success': False, 'error': 'No phone number available'}
        
        context = {
            'borrower_name': borrower.get_full_name(),
            'loan_number': loan.loan_number,
            'disbursed_amount': loan.disbursed_amount,
            'disbursement_date': loan.disbursement_date,
            'first_payment_date': loan.first_payment_date,
            'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Microfinance'),
        }
        
        message = render_to_string('sms/loan_disbursement.txt', context).strip()
        
        return self.send_sms(
            borrower.phone_number, 
            message, 
            template_name='loan_disbursement'
        )
    
    def send_savings_transaction(self, transaction):
        """Send savings transaction SMS."""
        account = transaction.savings_account
        borrower = account.borrower
        
        if not borrower.phone_number:
            return {'success': False, 'error': 'No phone number available'}
        
        context = {
            'borrower_name': borrower.get_full_name(),
            'transaction_type': transaction.get_transaction_type_display(),
            'amount': transaction.amount,
            'account_number': account.account_number,
            'balance': account.balance,
            'transaction_date': transaction.transaction_date,
            'organization_name': getattr(settings, 'ORGANIZATION_NAME', 'Microfinance'),
        }
        
        message = render_to_string('sms/savings_transaction.txt', context).strip()
        
        return self.send_sms(
            borrower.phone_number, 
            message, 
            template_name='savings_transaction'
        )
    
    def _clean_phone_number(self, phone_number: str) -> str:
        """Clean and format phone number."""
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if not present (assuming India +91)
        if len(cleaned) == 10:
            cleaned = '91' + cleaned
        elif len(cleaned) == 11 and cleaned.startswith('0'):
            cleaned = '91' + cleaned[1:]
        
        return cleaned
    
    def _log_sms(self, phone_number: str, message: str, template_name: str, result: Dict[str, Any]):
        """Log SMS for audit purposes."""
        try:
            from .models import SMSLog
            SMSLog.objects.create(
                phone_number=phone_number,
                message=message[:500],  # Truncate long messages
                template_name=template_name,
                provider=self.provider,
                status='sent' if result.get('success') else 'failed',
                provider_response=json.dumps(result)[:1000],
                sent_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Failed to log SMS: {str(e)}")


class TwilioSMSService:
    """Twilio SMS service implementation."""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '')
    
    def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Twilio."""
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            message_obj = client.messages.create(
                body=message,
                from_=self.from_number,
                to=f'+{phone_number}'
            )
            
            return {
                'success': True,
                'provider': 'twilio',
                'message_sid': message_obj.sid,
                'status': message_obj.status
            }
            
        except Exception as e:
            return {
                'success': False,
                'provider': 'twilio',
                'error': str(e)
            }


class TextLocalSMSService:
    """TextLocal SMS service implementation."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'TEXTLOCAL_API_KEY', '')
        self.sender = getattr(settings, 'TEXTLOCAL_SENDER', 'TXTLCL')
        self.base_url = 'https://api.textlocal.in/send/'
    
    def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via TextLocal."""
        try:
            data = {
                'apikey': self.api_key,
                'numbers': phone_number,
                'message': message,
                'sender': self.sender
            }
            
            response = requests.post(self.base_url, data=data)
            result = response.json()
            
            if result.get('status') == 'success':
                return {
                    'success': True,
                    'provider': 'textlocal',
                    'message_id': result.get('messages', [{}])[0].get('id'),
                    'cost': result.get('cost')
                }
            else:
                return {
                    'success': False,
                    'provider': 'textlocal',
                    'error': result.get('errors', [{}])[0].get('message', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'provider': 'textlocal',
                'error': str(e)
            }


class MSG91SMSService:
    """MSG91 SMS service implementation."""
    
    def __init__(self):
        self.auth_key = getattr(settings, 'MSG91_AUTH_KEY', '')
        self.sender_id = getattr(settings, 'MSG91_SENDER_ID', 'MSGIND')
        self.base_url = 'https://api.msg91.com/api/sendhttp.php'
    
    def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via MSG91."""
        try:
            params = {
                'authkey': self.auth_key,
                'mobiles': phone_number,
                'message': message,
                'sender': self.sender_id,
                'route': '4'
            }
            
            response = requests.get(self.base_url, params=params)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'provider': 'msg91',
                    'response': response.text
                }
            else:
                return {
                    'success': False,
                    'provider': 'msg91',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'provider': 'msg91',
                'error': str(e)
            }


class DummySMSService:
    """Dummy SMS service for testing."""
    
    def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Simulate SMS sending."""
        logger.info(f"DUMMY SMS to {phone_number}: {message}")
        return {
            'success': True,
            'provider': 'dummy',
            'message': 'SMS simulated successfully'
        }


# Global SMS service instance
sms_service = SMSService()


