from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Add missing external_reference column to repayments_payment table'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                # Check if column exists
                cursor.execute("PRAGMA table_info(repayments_payment);")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'external_reference' not in columns:
                    cursor.execute("ALTER TABLE repayments_payment ADD COLUMN external_reference VARCHAR(100);")
                    self.stdout.write(
                        self.style.SUCCESS('Successfully added external_reference column')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('external_reference column already exists')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error adding column: {e}')
                )
