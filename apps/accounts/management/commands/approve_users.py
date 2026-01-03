"""
Management command to approve pending user registrations.
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from apps.accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Approve pending user registrations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Approve specific username',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Approve all pending users',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all pending users',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_pending_users()
        elif options['all']:
            self.approve_all_users()
        elif options['username']:
            self.approve_user(options['username'])
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify --list, --all, or --username <username>'
                )
            )

    def list_pending_users(self):
        """List all pending users."""
        pending_users = CustomUser.objects.filter(is_active=False)
        
        if not pending_users.exists():
            self.stdout.write(
                self.style.SUCCESS('No pending users found.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'Found {pending_users.count()} pending users:')
        )
        
        for user in pending_users:
            self.stdout.write(
                f'  - {user.username} ({user.get_full_name()}) - {user.email}'
            )

    def approve_all_users(self):
        """Approve all pending users."""
        pending_users = CustomUser.objects.filter(is_active=False)
        
        if not pending_users.exists():
            self.stdout.write(
                self.style.SUCCESS('No pending users to approve.')
            )
            return
        
        count = 0
        for user in pending_users:
            if self.approve_user_account(user):
                count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully approved {count} users.')
        )

    def approve_user(self, username):
        """Approve a specific user."""
        try:
            user = CustomUser.objects.get(username=username, is_active=False)
            if self.approve_user_account(user):
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully approved user: {username}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to approve user: {username}')
                )
        except CustomUser.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User not found or already active: {username}')
            )

    def approve_user_account(self, user):
        """Approve a user account and send notification email."""
        try:
            # Activate the user
            user.is_active = True
            user.save()
            
            # Send approval email
            self.send_approval_email(user)
            
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error approving user {user.username}: {str(e)}')
            )
            return False

    def send_approval_email(self, user):
        """Send approval notification email."""
        subject = 'Account Approved - Golam Financial Services'
        message = f"""
Dear {user.get_full_name()},

Congratulations! Your account with Golam Financial Services has been approved.

You can now log in to your account using:
- Username: {user.username}
- Login URL: http://127.0.0.1:8000/login/

Welcome to Golam Financial Services!

Best regards,
Golam Financial Services Team
Nanenane - Morogoro, Tanzania
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS(f'Approval email sent to {user.email}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Failed to send email to {user.email}: {str(e)}')
            )
