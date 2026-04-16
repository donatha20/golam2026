"""
Management command to backup and restore database.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.management import call_command
from pathlib import Path
import subprocess
import datetime
import os
import shutil


class Command(BaseCommand):
    help = 'Backup and restore database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create database backup',
        )
        parser.add_argument(
            '--restore',
            type=str,
            help='Restore from backup file',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List available backups',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old backups (keep last 10)',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Backup directory (default: backups)',
        )

    def handle(self, *args, **options):
        self.backup_dir = Path(options['output_dir'])
        self.backup_dir.mkdir(exist_ok=True)

        if options['backup']:
            self.create_backup()
        elif options['restore']:
            self.restore_backup(options['restore'])
        elif options['list']:
            self.list_backups()
        elif options['cleanup']:
            self.cleanup_backups()
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --backup, --restore, --list, or --cleanup')
            )

    def create_backup(self):
        """Create a database backup."""
        self.stdout.write('💾 Creating database backup...')
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        db_config = settings.DATABASES['default']
        engine = db_config['ENGINE']
        
        if 'sqlite' in engine:
            self.backup_sqlite(timestamp)
        elif 'postgresql' in engine:
            self.backup_postgresql(timestamp, db_config)
        elif 'mysql' in engine:
            self.backup_mysql(timestamp, db_config)
        else:
            raise CommandError(f'Backup not supported for {engine}')

    def backup_sqlite(self, timestamp):
        """Backup SQLite database."""
        db_path = Path(settings.DATABASES['default']['NAME'])
        backup_path = self.backup_dir / f'backup_sqlite_{timestamp}.db'
        
        try:
            shutil.copy2(db_path, backup_path)
            
            # Also create a SQL dump
            sql_backup_path = self.backup_dir / f'backup_sqlite_{timestamp}.sql'
            with open(sql_backup_path, 'w') as f:
                call_command('dumpdata', stdout=f, format='json', indent=2)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ SQLite backup created: {backup_path}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ JSON dump created: {sql_backup_path}')
            )
            
        except Exception as e:
            raise CommandError(f'Failed to backup SQLite: {e}')

    def backup_postgresql(self, timestamp, db_config):
        """Backup PostgreSQL database."""
        backup_path = self.backup_dir / f'backup_postgresql_{timestamp}.sql'
        
        # Build pg_dump command
        cmd = ['pg_dump']
        
        if db_config.get('HOST'):
            cmd.extend(['-h', db_config['HOST']])
        if db_config.get('PORT'):
            cmd.extend(['-p', str(db_config['PORT'])])
        if db_config.get('USER'):
            cmd.extend(['-U', db_config['USER']])
        
        cmd.extend(['-f', str(backup_path)])
        cmd.append(db_config['NAME'])
        
        # Set password environment variable if provided
        env = os.environ.copy()
        if db_config.get('PASSWORD'):
            env['PGPASSWORD'] = db_config['PASSWORD']
        
        try:
            subprocess.run(cmd, check=True, env=env)
            self.stdout.write(
                self.style.SUCCESS(f'✅ PostgreSQL backup created: {backup_path}')
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Failed to backup PostgreSQL: {e}')

    def backup_mysql(self, timestamp, db_config):
        """Backup MySQL database."""
        backup_path = self.backup_dir / f'backup_mysql_{timestamp}.sql'
        
        # Build mysqldump command
        cmd = ['mysqldump']
        
        if db_config.get('HOST'):
            cmd.extend(['-h', db_config['HOST']])
        if db_config.get('PORT'):
            cmd.extend(['-P', str(db_config['PORT'])])
        if db_config.get('USER'):
            cmd.extend(['-u', db_config['USER']])
        if db_config.get('PASSWORD'):
            cmd.extend(['-p' + db_config['PASSWORD']])
        
        cmd.extend(['--single-transaction', '--routines', '--triggers'])
        cmd.append(db_config['NAME'])
        
        try:
            with open(backup_path, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ MySQL backup created: {backup_path}')
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Failed to backup MySQL: {e}')

    def restore_backup(self, backup_file):
        """Restore database from backup."""
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            # Try looking in backup directory
            backup_path = self.backup_dir / backup_file
            if not backup_path.exists():
                raise CommandError(f'Backup file not found: {backup_file}')
        
        self.stdout.write(f'🔄 Restoring from backup: {backup_path}')
        
        # Confirm restoration
        confirm = input('⚠️  This will overwrite the current database. Continue? (y/N): ')
        if confirm.lower() != 'y':
            self.stdout.write('❌ Restoration cancelled')
            return
        
        db_config = settings.DATABASES['default']
        engine = db_config['ENGINE']
        
        if 'sqlite' in engine:
            self.restore_sqlite(backup_path)
        elif 'postgresql' in engine:
            self.restore_postgresql(backup_path, db_config)
        elif 'mysql' in engine:
            self.restore_mysql(backup_path, db_config)
        else:
            raise CommandError(f'Restore not supported for {engine}')

    def restore_sqlite(self, backup_path):
        """Restore SQLite database."""
        db_path = Path(settings.DATABASES['default']['NAME'])
        
        try:
            if backup_path.suffix == '.db':
                # Direct database file
                shutil.copy2(backup_path, db_path)
            elif backup_path.suffix == '.sql':
                # SQL dump - use Django's loaddata
                call_command('flush', '--noinput')
                call_command('loaddata', str(backup_path))
            
            self.stdout.write(
                self.style.SUCCESS('✅ SQLite database restored')
            )
        except Exception as e:
            raise CommandError(f'Failed to restore SQLite: {e}')

    def restore_postgresql(self, backup_path, db_config):
        """Restore PostgreSQL database."""
        # Build psql command
        cmd = ['psql']
        
        if db_config.get('HOST'):
            cmd.extend(['-h', db_config['HOST']])
        if db_config.get('PORT'):
            cmd.extend(['-p', str(db_config['PORT'])])
        if db_config.get('USER'):
            cmd.extend(['-U', db_config['USER']])
        
        cmd.extend(['-f', str(backup_path)])
        cmd.append(db_config['NAME'])
        
        # Set password environment variable if provided
        env = os.environ.copy()
        if db_config.get('PASSWORD'):
            env['PGPASSWORD'] = db_config['PASSWORD']
        
        try:
            subprocess.run(cmd, check=True, env=env)
            self.stdout.write(
                self.style.SUCCESS('✅ PostgreSQL database restored')
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Failed to restore PostgreSQL: {e}')

    def restore_mysql(self, backup_path, db_config):
        """Restore MySQL database."""
        # Build mysql command
        cmd = ['mysql']
        
        if db_config.get('HOST'):
            cmd.extend(['-h', db_config['HOST']])
        if db_config.get('PORT'):
            cmd.extend(['-P', str(db_config['PORT'])])
        if db_config.get('USER'):
            cmd.extend(['-u', db_config['USER']])
        if db_config.get('PASSWORD'):
            cmd.extend(['-p' + db_config['PASSWORD']])
        
        cmd.append(db_config['NAME'])
        
        try:
            with open(backup_path, 'r') as f:
                subprocess.run(cmd, stdin=f, check=True)
            
            self.stdout.write(
                self.style.SUCCESS('✅ MySQL database restored')
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Failed to restore MySQL: {e}')

    def list_backups(self):
        """List available backups."""
        self.stdout.write('📋 Available backups:')
        
        backup_files = sorted(self.backup_dir.glob('backup_*'), reverse=True)
        
        if not backup_files:
            self.stdout.write('  No backups found')
            return
        
        for backup_file in backup_files:
            size = backup_file.stat().st_size / (1024 * 1024)  # MB
            mtime = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
            self.stdout.write(
                f'  {backup_file.name} ({size:.2f} MB, {mtime.strftime("%Y-%m-%d %H:%M:%S")})'
            )

    def cleanup_backups(self):
        """Clean up old backups, keeping the last 10."""
        self.stdout.write('🧹 Cleaning up old backups...')
        
        backup_files = sorted(self.backup_dir.glob('backup_*'), reverse=True)
        
        if len(backup_files) <= 10:
            self.stdout.write('  No cleanup needed')
            return
        
        files_to_delete = backup_files[10:]
        
        for backup_file in files_to_delete:
            backup_file.unlink()
            self.stdout.write(f'  Deleted: {backup_file.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Cleaned up {len(files_to_delete)} old backups')
        )


