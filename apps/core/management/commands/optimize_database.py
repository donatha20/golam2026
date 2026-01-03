"""
Management command to optimize database performance.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Optimize database performance with indexes and query analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze-queries',
            action='store_true',
            help='Analyze slow queries',
        )
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create recommended indexes',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Vacuum database (SQLite/PostgreSQL)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔧 Starting Database Optimization...\n')
        )

        if options['analyze_queries']:
            self.analyze_queries()

        if options['create_indexes']:
            self.create_recommended_indexes()

        if options['vacuum']:
            self.vacuum_database()

        self.stdout.write(
            self.style.SUCCESS('\n✅ Database optimization completed!')
        )

    def analyze_queries(self):
        """Analyze database queries for optimization opportunities."""
        self.stdout.write('📊 Analyzing database queries...')
        
        with connection.cursor() as cursor:
            # Check database engine
            db_engine = settings.DATABASES['default']['ENGINE']
            
            if 'sqlite' in db_engine:
                self.analyze_sqlite_queries(cursor)
            elif 'postgresql' in db_engine:
                self.analyze_postgresql_queries(cursor)
            elif 'mysql' in db_engine:
                self.analyze_mysql_queries(cursor)
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Query analysis not supported for this database engine')
                )

    def analyze_sqlite_queries(self, cursor):
        """Analyze SQLite queries."""
        # Get table statistics
        cursor.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = cursor.fetchall()
        
        self.stdout.write(f'📋 Found {len(tables)} tables')
        
        for table_name, sql in tables:
            if table_name.startswith('django_'):
                continue
                
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            if row_count > 1000:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Large table: {table_name} ({row_count} rows)')
                )

    def analyze_postgresql_queries(self, cursor):
        """Analyze PostgreSQL queries."""
        # Get table statistics
        cursor.execute("""
            SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
        """)
        
        stats = cursor.fetchall()
        self.stdout.write('📊 Table Statistics:')
        for schema, table, inserts, updates, deletes, live_tuples in stats[:10]:
            self.stdout.write(f'  {table}: {live_tuples} rows, {inserts} inserts, {updates} updates')

    def analyze_mysql_queries(self, cursor):
        """Analyze MySQL queries."""
        cursor.execute("SHOW TABLE STATUS")
        stats = cursor.fetchall()
        
        self.stdout.write('📊 Table Statistics:')
        for stat in stats:
            table_name = stat[0]
            rows = stat[4] or 0
            if rows > 1000:
                self.stdout.write(f'  {table_name}: {rows} rows')

    def create_recommended_indexes(self):
        """Create recommended database indexes."""
        self.stdout.write('🔍 Creating recommended indexes...')
        
        indexes = [
            # Borrowers indexes
            "CREATE INDEX IF NOT EXISTS idx_borrowers_phone ON borrowers_borrower(phone_number);",
            "CREATE INDEX IF NOT EXISTS idx_borrowers_status ON borrowers_borrower(status);",
            "CREATE INDEX IF NOT EXISTS idx_borrowers_created ON borrowers_borrower(created_at);",
            
            # Loans indexes
            "CREATE INDEX IF NOT EXISTS idx_loans_status ON loans_loan(status);",
            "CREATE INDEX IF NOT EXISTS idx_loans_borrower ON loans_loan(borrower_id);",
            "CREATE INDEX IF NOT EXISTS idx_loans_disbursement ON loans_loan(disbursement_date);",
            "CREATE INDEX IF NOT EXISTS idx_loans_maturity ON loans_loan(maturity_date);",
            "CREATE INDEX IF NOT EXISTS idx_loans_outstanding ON loans_loan(outstanding_balance);",
            
            # Repayment Schedule indexes
            "CREATE INDEX IF NOT EXISTS idx_schedule_due_date ON loans_repaymentschedule(due_date);",
            "CREATE INDEX IF NOT EXISTS idx_schedule_status ON loans_repaymentschedule(status);",
            "CREATE INDEX IF NOT EXISTS idx_schedule_loan ON loans_repaymentschedule(loan_id);",
            
            # Repayments indexes
            "CREATE INDEX IF NOT EXISTS idx_repayments_date ON loans_repayment(payment_date);",
            "CREATE INDEX IF NOT EXISTS idx_repayments_schedule ON loans_repayment(schedule_id);",
            
            # Savings indexes
            "CREATE INDEX IF NOT EXISTS idx_savings_account ON savings_savingsaccount(account_number);",
            "CREATE INDEX IF NOT EXISTS idx_savings_borrower ON savings_savingsaccount(borrower_id);",
            "CREATE INDEX IF NOT EXISTS idx_savings_status ON savings_savingsaccount(status);",
            
            # Transactions indexes
            "CREATE INDEX IF NOT EXISTS idx_transactions_date ON savings_savingstransaction(transaction_date);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_account ON savings_savingstransaction(account_id);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON savings_savingstransaction(transaction_type);",
            
            # Journal Entries indexes
            "CREATE INDEX IF NOT EXISTS idx_journal_date ON accounting_journalentry(entry_date);",
            "CREATE INDEX IF NOT EXISTS idx_journal_status ON accounting_journalentry(status);",
            "CREATE INDEX IF NOT EXISTS idx_journal_reference ON accounting_journalentry(reference_number);",
            
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_loans_borrower_status ON loans_loan(borrower_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_schedule_loan_status ON loans_repaymentschedule(loan_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON savings_savingstransaction(account_id, transaction_date);",
        ]
        
        with connection.cursor() as cursor:
            created_count = 0
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    created_count += 1
                except Exception as e:
                    # Index might already exist
                    if 'already exists' not in str(e).lower():
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Failed to create index: {str(e)}')
                        )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created/verified {created_count} indexes')
            )

    def vacuum_database(self):
        """Vacuum database to reclaim space and update statistics."""
        self.stdout.write('🧹 Vacuuming database...')
        
        db_engine = settings.DATABASES['default']['ENGINE']
        
        with connection.cursor() as cursor:
            if 'sqlite' in db_engine:
                cursor.execute("VACUUM;")
                cursor.execute("ANALYZE;")
                self.stdout.write('✅ SQLite database vacuumed and analyzed')
                
            elif 'postgresql' in db_engine:
                # PostgreSQL VACUUM cannot be run inside a transaction
                connection.set_autocommit(True)
                cursor.execute("VACUUM ANALYZE;")
                connection.set_autocommit(False)
                self.stdout.write('✅ PostgreSQL database vacuumed and analyzed')
                
            elif 'mysql' in db_engine:
                cursor.execute("OPTIMIZE TABLE borrowers_borrower;")
                cursor.execute("OPTIMIZE TABLE loans_loan;")
                cursor.execute("OPTIMIZE TABLE loans_repaymentschedule;")
                cursor.execute("OPTIMIZE TABLE savings_savingsaccount;")
                self.stdout.write('✅ MySQL tables optimized')
                
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Vacuum not supported for this database engine')
                )

    def get_database_size(self):
        """Get database size information."""
        db_engine = settings.DATABASES['default']['ENGINE']
        
        with connection.cursor() as cursor:
            if 'sqlite' in db_engine:
                db_path = settings.DATABASES['default']['NAME']
                import os
                size = os.path.getsize(db_path) / (1024 * 1024)  # MB
                self.stdout.write(f'📊 Database size: {size:.2f} MB')
                
            elif 'postgresql' in db_engine:
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                size = cursor.fetchone()[0]
                self.stdout.write(f'📊 Database size: {size}')
                
            elif 'mysql' in db_engine:
                cursor.execute("""
                    SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size in MB'
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                """)
                size = cursor.fetchone()[0]
                self.stdout.write(f'📊 Database size: {size} MB')
