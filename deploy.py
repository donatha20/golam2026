#!/usr/bin/env python3
"""
Production deployment script for Golam Microfinance System.
This script automates the deployment process and ensures all requirements are met.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

class DeploymentManager:
    def __init__(self, environment='production'):
        self.environment = environment
        self.base_dir = Path(__file__).resolve().parent
        self.venv_path = self.base_dir / 'venv'
        
    def run_command(self, command, check=True):
        """Run a shell command and return the result."""
        print(f"🔄 Running: {command}")
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=check, 
                capture_output=True, 
                text=True,
                cwd=self.base_dir
            )
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running command: {command}")
            print(f"Error: {e.stderr}")
            if check:
                sys.exit(1)
            return e

    def check_python_version(self):
        """Check if Python version is compatible."""
        print("🐍 Checking Python version...")
        version = sys.version_info
        if version.major != 3 or version.minor < 8:
            print("❌ Python 3.8+ is required")
            sys.exit(1)
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")

    def setup_virtual_environment(self):
        """Set up virtual environment if it doesn't exist."""
        print("🔧 Setting up virtual environment...")
        if not self.venv_path.exists():
            self.run_command(f"python -m venv {self.venv_path}")
        
        # Activate virtual environment
        if os.name == 'nt':  # Windows
            activate_script = self.venv_path / 'Scripts' / 'activate.bat'
            pip_path = self.venv_path / 'Scripts' / 'pip.exe'
        else:  # Unix/Linux
            activate_script = self.venv_path / 'bin' / 'activate'
            pip_path = self.venv_path / 'bin' / 'pip'
        
        print(f"✅ Virtual environment ready at {self.venv_path}")
        return pip_path

    def install_dependencies(self, pip_path):
        """Install Python dependencies."""
        print("📦 Installing dependencies...")
        self.run_command(f"{pip_path} install --upgrade pip")
        self.run_command(f"{pip_path} install -r requirements.txt")
        print("✅ Dependencies installed")

    def setup_environment_file(self):
        """Set up environment file."""
        print("🔐 Setting up environment configuration...")
        env_file = self.base_dir / '.env'
        env_example = self.base_dir / '.env.example'
        
        if not env_file.exists() and env_example.exists():
            print("⚠️  .env file not found. Creating from .env.example")
            env_file.write_text(env_example.read_text())
            print("📝 Please edit .env file with your configuration")
        elif env_file.exists():
            print("✅ Environment file exists")
        else:
            print("❌ No .env or .env.example file found")
            sys.exit(1)

    def run_migrations(self):
        """Run database migrations."""
        print("🗄️  Running database migrations...")
        self.run_command("python manage.py makemigrations")
        self.run_command("python manage.py migrate")
        print("✅ Migrations completed")

    def collect_static_files(self):
        """Collect static files."""
        print("📁 Collecting static files...")
        self.run_command("python manage.py collectstatic --noinput")
        print("✅ Static files collected")

    def create_superuser(self):
        """Create superuser if none exists."""
        print("👤 Checking for superuser...")
        result = self.run_command(
            "python manage.py shell -c \"from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(is_superuser=True).exists())\"",
            check=False
        )
        
        if "True" not in result.stdout:
            print("👤 Creating superuser...")
            print("Please enter superuser details:")
            self.run_command("python manage.py createsuperuser")
        else:
            print("✅ Superuser already exists")

    def run_health_check(self):
        """Run system health check."""
        print("🏥 Running system health check...")
        self.run_command("python manage.py system_health_check")

    def setup_systemd_service(self):
        """Set up systemd service for production."""
        if self.environment != 'production':
            return
            
        print("⚙️  Setting up systemd service...")
        service_content = f"""[Unit]
Description=Golam Microfinance System
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory={self.base_dir}
Environment=DJANGO_SETTINGS_MODULE=microfinance_system.settings.production
ExecStart={self.venv_path}/bin/gunicorn microfinance_system.wsgi:application --bind 0.0.0.0:8000
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
"""
        
        service_file = Path('/etc/systemd/system/microfinance.service')
        try:
            service_file.write_text(service_content)
            self.run_command("systemctl daemon-reload")
            self.run_command("systemctl enable microfinance")
            print("✅ Systemd service configured")
        except PermissionError:
            print("⚠️  Need sudo privileges to set up systemd service")
            print("Run the following commands manually:")
            print(f"sudo tee /etc/systemd/system/microfinance.service << 'EOF'")
            print(service_content)
            print("EOF")
            print("sudo systemctl daemon-reload")
            print("sudo systemctl enable microfinance")

    def setup_nginx_config(self):
        """Set up nginx configuration."""
        if self.environment != 'production':
            return
            
        print("🌐 Setting up nginx configuration...")
        nginx_config = f"""server {{
    listen 80;
    server_name your-domain.com;
    
    location /static/ {{
        alias {self.base_dir}/staticfiles/;
    }}
    
    location /media/ {{
        alias {self.base_dir}/media/;
    }}
    
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        
        nginx_file = Path('/etc/nginx/sites-available/microfinance')
        try:
            nginx_file.write_text(nginx_config)
            sites_enabled = Path('/etc/nginx/sites-enabled/microfinance')
            if not sites_enabled.exists():
                sites_enabled.symlink_to(nginx_file)
            self.run_command("nginx -t")
            self.run_command("systemctl reload nginx")
            print("✅ Nginx configuration set up")
        except PermissionError:
            print("⚠️  Need sudo privileges to set up nginx")
            print("Nginx configuration saved to nginx.conf")
            with open('nginx.conf', 'w') as f:
                f.write(nginx_config)

    def deploy(self):
        """Run the complete deployment process."""
        print("🚀 Starting deployment process...")
        print(f"Environment: {self.environment}")
        print("="*50)
        
        self.check_python_version()
        pip_path = self.setup_virtual_environment()
        self.install_dependencies(pip_path)
        self.setup_environment_file()
        self.run_migrations()
        self.collect_static_files()
        self.create_superuser()
        
        if self.environment == 'production':
            self.setup_systemd_service()
            self.setup_nginx_config()
        
        self.run_health_check()
        
        print("="*50)
        print("🎉 Deployment completed successfully!")
        
        if self.environment == 'production':
            print("\n📋 Next steps:")
            print("1. Edit .env file with your production settings")
            print("2. Configure your domain in nginx config")
            print("3. Set up SSL certificate (Let's Encrypt recommended)")
            print("4. Start the service: sudo systemctl start microfinance")
            print("5. Check service status: sudo systemctl status microfinance")
        else:
            print("\n🔧 Development server:")
            print("Run: python manage.py runserver")


def main():
    parser = argparse.ArgumentParser(description='Deploy Golam Microfinance System')
    parser.add_argument(
        '--environment',
        choices=['development', 'staging', 'production'],
        default='production',
        help='Deployment environment'
    )
    
    args = parser.parse_args()
    
    deployer = DeploymentManager(args.environment)
    deployer.deploy()


if __name__ == '__main__':
    main()
