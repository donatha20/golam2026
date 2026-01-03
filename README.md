<div align="center">

# 🏦 Golam Microfinance Management System

[![Django](https://img.shields.io/badge/Django-5.2.3-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green. svg?style=for-the-badge)](LICENSE)

**A comprehensive, enterprise-grade microfinance management system built with Django**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Architecture](#-architecture) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [System Requirements](#-system-requirements)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [API Documentation](#-api-documentation)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

---

## 🌟 Overview

The **Golam Microfinance Management System** is a robust, full-featured web application designed to streamline microfinance operations.  Built with Django 5.2.3 and modern web technologies, it provides a complete solution for managing loans, borrowers, savings accounts, repayments, and financial operations with enterprise-level security and performance.

### Key Highlights

✅ **Comprehensive Loan Management** - From application to disbursement and repayment tracking  
✅ **Double-Entry Accounting** - Professional financial record-keeping with automated journal entries  
✅ **Advanced Reporting** - Real-time analytics with PDF/Excel export capabilities  
✅ **Multi-User Support** - Role-based access control for admins and loan officers  
✅ **SMS Integration** - Automated notifications and payment reminders  
✅ **Production-Ready** - Docker support, security hardened, and performance optimized  

---

## 🚀 Features

### Core Modules

#### 👥 Borrower Management
- Complete borrower lifecycle management
- KYC documentation and photo uploads
- Next of kin information tracking
- Borrower status management (Active/Suspended/Blacklisted)
- Advanced search and filtering

#### 💰 Loan Management
- Multiple loan types with configurable parameters
- Loan application and approval workflow
- Automated amortization schedule generation
- Interest calculation (simple and compound)
- Loan disbursement tracking
- Collateral management
- Overdue loan tracking and penalties

#### 💳 Savings Account Management
- Individual savings accounts
- Deposit and withdrawal tracking
- Interest calculation on savings
- Minimum balance enforcement
- Transaction history

#### 💸 Repayment Management
- Flexible payment collection (Daily/Weekly/Monthly)
- Multiple payment methods support
- Automated payment allocation
- Payment receipt generation
- Daily collection tracking
- Arrears management

#### 📊 Accounting & Financial Management
- Double-entry bookkeeping system
- Chart of accounts
- Automated journal entries
- Trial balance generation
- Financial statements (P&L, Balance Sheet)
- General ledger reporting

#### 🏢 Asset & Collateral Management
- Internal asset tracking
- Asset depreciation calculation
- Collateral valuation
- Document management
- Asset lifecycle management

#### 📈 Reports & Analytics
- Interactive dashboard with real-time metrics
- Loan portfolio analysis
- Collection reports
- Defaulter tracking
- Financial performance reports
- Custom report builder
- Export to PDF and Excel

#### 📱 Communication & CRM
- SMS notification system
- Automated payment reminders
- Bulk messaging capabilities
- Communication history tracking
- SMS service integration (Twilio)

### Advanced Features

🔐 **Security**
- Multi-factor authentication ready
- Role-based permissions (Admin, Loan Officer)
- CSRF and XSS protection
- SQL injection prevention
- Rate limiting
- Comprehensive audit logging
- Secure file uploads

⚡ **Performance**
- Query optimization with select_related/prefetch_related
- Database indexing strategy
- Redis caching layer
- Pagination for large datasets
- Celery for background tasks
- Database connection pooling

🎨 **User Experience**
- Responsive Bootstrap 5 interface
- Dark/Light theme toggle
- Mobile-friendly design
- Advanced filtering and search
- Inline editing capabilities
- Real-time form validation
- Chart.js data visualizations

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 5.2.3
- **Language**: Python 3.11+
- **ORM**: Django ORM
- **API**:  Django REST Framework (ready)
- **Task Queue**: Celery 5.3.4
- **Message Broker**: Redis 5.0.1

### Database
- **Primary**: PostgreSQL 13+ (Production)
- **Development**: SQLite3
- **Caching**: Redis

### Frontend
- **Framework**: Bootstrap 5
- **JavaScript**:  Vanilla JS + jQuery
- **Charts**: Chart.js
- **Icons**: Font Awesome
- **Forms**:  Crispy Forms with Bootstrap 5

### DevOps & Deployment
- **Web Server**: Nginx
- **WSGI Server**:  Gunicorn 21.2.0
- **Containerization**: Docker & Docker Compose
- **Static Files**: WhiteNoise 6.6.0
- **Process Manager**: Supervisor (optional)

### Integrations
- **SMS**: Twilio 8.5.0+
- **PDF Generation**: ReportLab 4.4.1
- **Excel Export**: OpenPyXL 3.1.5
- **Phone Numbers**: django-phonenumber-field 7.1.0+

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS, Windows 10+
- **Python**: 3.11 or higher
- **RAM**: 2GB (4GB recommended)
- **Storage**: 10GB free space
- **Database**: PostgreSQL 13+ or SQLite (dev only)

### Recommended for Production
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 2+ cores
- **RAM**: 4GB+
- **Storage**: 20GB+ SSD
- **Database**: PostgreSQL 14+
- **Cache**: Redis 6+

---

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/donatha20/golam2026.git
cd golam2026

# Copy environment file
cp .env.example .env

# Build and start services
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Access the application
# Main app: http://localhost:8000
# Admin:  http://localhost:8000/admin
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/donatha20/golam2026.git
cd golam2026

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example . env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run development server
python manage.py runserver

# Access at http://localhost:8000
```

---

## 📦 Installation

### Development Environment

#### 1. Prerequisites
```bash
# Install Python 3.11+
python --version

# Install PostgreSQL (optional for development)
sudo apt-get install postgresql postgresql-contrib

# Install Redis (optional for development)
sudo apt-get install redis-server
```

#### 2. Clone and Setup
```bash
# Clone repository
git clone https://github.com/donatha20/golam2026.git
cd golam2026

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Database Setup
```bash
# For PostgreSQL
createdb microfinance_db

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost:5432/microfinance_db

# Run migrations
python manage.py migrate

# Load sample data (optional)
python manage.py loaddata fixtures/sample_data.json
```

#### 4. Create Admin User
```bash
python manage.py createsuperuser
```

#### 5. Run Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

### Production Environment

See [Deployment](#-deployment) section for production setup instructions.

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Environment
ENVIRONMENT=development  # development, staging, production
SECRET_KEY=your-secret-key-here
DEBUG=True

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/microfinance_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@golamfinancial.co.tz

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Security Settings (Production)
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Sentry (Error Tracking - Optional)
SENTRY_DSN=your-sentry-dsn

# Storage (AWS S3 - Optional)
USE_S3=False
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

### Application Settings

Key configuration files: 
- `microfinance_system/settings/base.py` - Base settings
- `microfinance_system/settings/development.py` - Development settings
- `microfinance_system/settings/production. py` - Production settings

---

## 📖 Usage

### Admin Panel

Access the Django admin at `http://localhost:8000/admin`

**Default Roles:**
- **Admin**: Full system access
- **Loan Officer**:  Limited access based on permissions

### Main Application

1. **Login**:  Navigate to `http://localhost:8000/login`
2. **Dashboard**: View system overview and key metrics
3. **Borrowers**: Manage borrower information
4. **Loans**: Create and manage loan applications
5. **Repayments**: Record and track payments
6. **Savings**: Manage savings accounts
7. **Reports**: Generate financial and operational reports

### Common Tasks

#### Register a New Borrower
```
Borrowers → Add New Borrower → Fill Form → Save
```

#### Create a Loan Application
```
Loans → New Loan Application → Select Borrower → Fill Details → Submit
```

#### Record a Payment
```
Repayments → New Payment → Select Loan → Enter Amount → Submit
```

#### Generate Reports
```
Reports → Select Report Type → Set Parameters → Generate → Export
```

---

## 📁 Project Structure

```
golam2026/
├── apps/                           # Django applications
│   ├── accounts/                   # User management
│   ├── borrowers/                  # Borrower management
│   ├── loans/                      # Loan management
│   ├── repayments/                 # Payment processing
│   ├── savings/                    # Savings accounts
│   ├── accounting/                 # Financial records
│   ├── assets/                     # Asset & collateral management
│   ├── crm/                        # Customer relationship management
│   ├── reports/                    # Analytics & reporting
│   ├── settings/                   # System configuration
│   └── core/                       # Shared utilities
│
├── microfinance_system/            # Main project directory
│   ├── settings/                   # Settings modules
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── static/                         # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   ├── images/
│   └── fonts/
│
├── templates/                      # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── registration/
│   └── components/
│
├── media/                          # User-uploaded files
│   ├── borrower_photos/
│   ├── documents/
│   └── reports/
│
├── tests/                          # Test suite
│   ├── test_accounts/
│   ├── test_borrowers/
│   ├── test_loans/
│   └── fixtures/
│
├── docs/                           # Documentation
│   ├── DATABASE_SCHEMA.md
│   ├── PROJECT_STRUCTURE.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   └── SMS_SYSTEM_DOCUMENTATION.md
│
├── docker-compose.yml              # Docker Compose configuration
├── Dockerfile                      # Docker image definition
├── nginx.conf                      # Nginx configuration
├── requirements.txt                # Python dependencies
├── manage.py                       # Django management script
├── pytest.ini                      # Pytest configuration
├── . env. example                    # Example environment file
├── . gitignore                      # Git ignore file
└── README.md                       # This file
```

For detailed structure, see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test types
pytest -m unit                      # Unit tests only
pytest -m integration               # Integration tests only
pytest -m security                  # Security tests only

# Run specific app tests
pytest tests/test_loans/

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

### Test Coverage

```bash
# Generate coverage report
coverage run -m pytest
coverage report
coverage html  # HTML report in htmlcov/
```

### Writing Tests

Example test structure:
```python
# tests/test_loans/test_models.py
import pytest
from apps.loans.models import Loan

@pytest.mark.unit
def test_loan_creation(db, sample_borrower):
    loan = Loan.objects.create(
        borrower=sample_borrower,
        amount_requested=10000,
        duration_months=12
    )
    assert loan.loan_number is not None
    assert loan.status == 'PENDING'
```

---

## 🚢 Deployment

### Production Deployment

#### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and configure
git clone https://github.com/donatha20/golam2026.git
cd golam2026

# 2. Set up environment
cp .env.example . env
nano .env  # Edit with production values

# 3. Build and start services
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose exec web python manage.py migrate

# 5. Create superuser
docker-compose exec web python manage.py createsuperuser

# 6. Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# 7. Set up SSL with Let's Encrypt (optional)
docker-compose run certbot certonly --webroot \
  -w /var/www/certbot \
  -d yourdomain.com
```

#### Option 2: Manual Deployment

```bash
# 1. Use the deployment script
python deploy.py --environment production

# 2. Configure Nginx
sudo cp nginx.conf /etc/nginx/sites-available/golam
sudo ln -s /etc/nginx/sites-available/golam /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 3. Set up Gunicorn service
sudo systemctl enable golam
sudo systemctl start golam

# 4. Set up Celery workers
sudo systemctl enable celery
sudo systemctl start celery
```

### Deployment Checklist

- [ ] Update `SECRET_KEY` in production
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up PostgreSQL database
- [ ] Configure Redis
- [ ] Set up email service
- [ ] Configure SMS service (Twilio)
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring (Sentry)
- [ ] Configure backups
- [ ] Set up log rotation
- [ ] Enable security headers
- [ ] Test all critical functionality

For complete checklist, see [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md).

---

## 📚 API Documentation

### REST API Endpoints (Coming Soon)

The system is built with Django REST Framework ready for API integration. 

Planned endpoints:
- `/api/v1/borrowers/` - Borrower CRUD operations
- `/api/v1/loans/` - Loan management
- `/api/v1/repayments/` - Payment processing
- `/api/v1/savings/` - Savings account operations
- `/api/v1/reports/` - Report generation

### Authentication

API authentication will support:
- Token-based authentication
- JWT tokens
- OAuth2 (planned)

---

## 🔒 Security

### Security Features

✅ **Authentication & Authorization**
- Django's built-in authentication system
- Custom user model with role-based permissions
- Session management
- Password hashing (PBKDF2)

✅ **Data Protection**
- CSRF protection enabled
- XSS protection with template escaping
- SQL injection prevention (Django ORM)
- Secure password storage
- Input validation and sanitization

✅ **Network Security**
- HTTPS enforcement in production
- Secure cookies (HttpOnly, Secure, SameSite)
- HSTS headers
- X-Frame-Options protection

✅ **Application Security**
- Rate limiting on sensitive endpoints
- File upload validation
- Comprehensive audit logging
- Security headers middleware
- Regular dependency updates

### Security Best Practices

1. **Always use HTTPS in production**
2. **Keep SECRET_KEY private and random**
3. **Update dependencies regularly**
4. **Enable all security middleware**
5. **Use strong passwords**
6. **Implement backup strategies**
7. **Monitor logs for suspicious activity**
8. **Regular security audits**

### Reporting Security Issues

Please report security vulnerabilities to:  **security@golamfinancial. co.tz**

Do not create public GitHub issues for security vulnerabilities.

---

## 🤝 Contributing

We welcome contributions from the community! 

### How to Contribute

1. **Fork the repository**
   ```bash
   git clone https://github.com/donatha20/golam2026.git
   cd golam2026
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Follow PEP 8 style guide
   - Write tests for new features
   - Update documentation

4. **Run tests**
   ```bash
   pytest
   ```

5. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Open a Pull Request**
   - Provide clear description
   - Reference related issues
   - Ensure CI passes

### Development Guidelines

- **Code Style**: Follow PEP 8
- **Commits**: Use conventional commits
- **Testing**:  Maintain >80% code coverage
- **Documentation**: Update docs for new features
- **Review**: All PRs require review before merge

### Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 Golam Financial

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction... 
```

---

## 📞 Support

### Getting Help

- **📧 Email**: admin@golamfinancial.co.tz
- **📖 Documentation**: [docs/](docs/)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/donatha20/golam2026/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/donatha20/golam2026/discussions)

### Commercial Support

For enterprise support, customization, and training:
- **Email**: enterprise@golamfinancial.co.tz
- **Website**: https://golamfinancial.co.tz

---

## 🙏 Acknowledgments

- Django Software Foundation
- Bootstrap Team
- All open-source contributors
- The microfinance community

---

## 📊 Project Status

- **Version**: 2.0
- **Status**: Active Development
- **Last Updated**: January 2026
- **Maintained**: Yes ✅

---

## 🗺️ Roadmap

### Current Release (v2.0)
- ✅ Core microfinance functionality
- ✅ Double-entry accounting
- ✅ SMS integration
- ✅ Reporting system

### Upcoming (v2.1)
- 🔄 Mobile app (React Native)
- 🔄 REST API completion
- 🔄 Advanced analytics dashboard
- 🔄 Multi-branch support

### Future (v3.0)
- 📅 Mobile money integration
- 📅 Blockchain for audit trail
- 📅 AI-powered credit scoring
- 📅 Multi-currency support

---

<div align="center">

**⭐ Star this repo if you find it helpful!**

Made with ❤️ by @donatha20

[Report Bug](https://github.com/donatha20/golam2026/issues) • [Request Feature](https://github.com/donatha20/golam2026/issues) • [Documentation](docs/)

</div>
