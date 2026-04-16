"""
Management command to perform comprehensive system health checks.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.test import Client
import os
import sys
from pathlib import Path

User = get_user_model()


class Command(BaseCommand):
    help = 'Perform comprehensive system health checks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
        parser.add_argument(
            '--email-test',
            action='store_true',
            help='Test email functionality',
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.email_test = options['email_test']
        
        self.stdout.write(
            self.style.SUCCESS('🏥 Starting System Health Check...\n')
        )
        
        checks = [
            self.check_database,
            self.check_cache,
            self.check_static_files,
            self.check_media_files,
            self.check_logs_directory,
            self.check_environment_variables,
            self.check_user_model,
            self.check_apps_installed,
            self.check_migrations,
            self.check_permissions,
        ]
        
        if self.email_test:
            checks.append(self.check_email)
        
        passed = 0
        failed = 0
        
        for check in checks:
            try:
                if check():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ {check.__name__}: {str(e)}')
                )
                failed += 1
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'✅ Passed: {passed}')
        )
        if failed > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed: {failed}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('🎉 All health checks passed!')
            )
        self.stdout.write('='*50)

    def check_database(self):
        """Check database connectivity and basic operations."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    self.stdout.write(
                        self.style.SUCCESS('✅ Database: Connection successful')
                    )
                    return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database: {str(e)}')
            )
            return False

    def check_cache(self):
        """Check cache functionality."""
        try:
            cache.set('health_check', 'test_value', 30)
            value = cache.get('health_check')
            if value == 'test_value':
                cache.delete('health_check')
                self.stdout.write(
                    self.style.SUCCESS('✅ Cache: Working correctly')
                )
                return True
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Cache: Value mismatch')
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Cache: {str(e)}')
            )
            return False

    def check_static_files(self):
        """Check static files configuration."""
        try:
            static_root = Path(settings.STATIC_ROOT)
            if static_root.exists():
                self.stdout.write(
                    self.style.SUCCESS('✅ Static Files: Directory exists')
                )
                return True
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Static Files: Directory does not exist (run collectstatic)')
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Static Files: {str(e)}')
            )
            return False

    def check_media_files(self):
        """Check media files configuration."""
        try:
            media_root = Path(settings.MEDIA_ROOT)
            if not media_root.exists():
                media_root.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = media_root / 'health_check.txt'
            test_file.write_text('test')
            test_file.unlink()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Media Files: Directory accessible and writable')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Media Files: {str(e)}')
            )
            return False

    def check_logs_directory(self):
        """Check logs directory."""
        try:
            logs_dir = Path(settings.BASE_DIR) / 'logs'
            if not logs_dir.exists():
                logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = logs_dir / 'health_check.log'
            test_file.write_text('test')
            test_file.unlink()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Logs Directory: Accessible and writable')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Logs Directory: {str(e)}')
            )
            return False

    def check_environment_variables(self):
        """Check critical environment variables."""
        required_vars = ['SECRET_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not getattr(settings, var, None):
                missing_vars.append(var)
        
        if missing_vars:
            self.stdout.write(
                self.style.ERROR(f'❌ Environment: Missing variables: {", ".join(missing_vars)}')
            )
            return False
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ Environment: All required variables present')
            )
            return True

    def check_user_model(self):
        """Check user model functionality."""
        try:
            user_count = User.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f'✅ User Model: {user_count} users in database')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ User Model: {str(e)}')
            )
            return False

    def check_apps_installed(self):
        """Check that all required apps are properly installed."""
        try:
            from django.apps import apps
            app_configs = apps.get_app_configs()
            local_apps = [app for app in app_configs if app.name.startswith('apps.')]
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Apps: {len(local_apps)} local apps installed')
            )
            
            if self.verbose:
                for app in local_apps:
                    self.stdout.write(f'   - {app.name}')
            
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Apps: {str(e)}')
            )
            return False

    def check_migrations(self):
        """Check migration status."""
        try:
            from django.core.management import execute_from_command_line
            from io import StringIO
            import sys
            
            # Capture output
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                execute_from_command_line(['manage.py', 'showmigrations', '--plan'])
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            
            if '[X]' in output and '[ ]' not in output:
                self.stdout.write(
                    self.style.SUCCESS('✅ Migrations: All migrations applied')
                )
                return True
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Migrations: Unapplied migrations found')
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Migrations: {str(e)}')
            )
            return False

    def check_permissions(self):
        """Check file system permissions."""
        try:
            # Check if we can write to BASE_DIR
            test_file = Path(settings.BASE_DIR) / 'health_check_permissions.txt'
            test_file.write_text('test')
            test_file.unlink()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Permissions: File system writable')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Permissions: {str(e)}')
            )
            return False

    def check_email(self):
        """Check email functionality."""
        try:
            send_mail(
                'Health Check Test',
                'This is a test email from the health check system.',
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMINS[0][1]] if settings.ADMINS else ['test@example.com'],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS('✅ Email: Test email sent successfully')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Email: {str(e)}')
            )
            return False


