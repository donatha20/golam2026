# Golam Microfinance System

A comprehensive microfinance management system built with Django, designed for managing loans, savings, borrowers, and financial operations.

## 🚀 Features

### Core Modules
- **👥 Borrower Management**: Complete borrower lifecycle management
- **💰 Loan Management**: Loan applications, approvals, disbursements, and tracking
- **💳 Savings Management**: Savings accounts and transaction management
- **💸 Repayment Management**: Payment tracking and schedule management
- **📊 Financial Statements**: Trial balance, journal entries, and reporting
- **🏦 Accounting**: Chart of accounts and financial tracking
- **📈 Finance Tracker**: Financial analytics and insights
- **🏢 Asset Management**: Asset tracking and management

### Advanced Features
- **🔐 Security**: Multi-layer security with rate limiting, CSRF protection, and audit logging
- **⚡ Performance**: Optimized database queries, caching, and pagination
- **📱 Responsive Design**: Mobile-friendly interface with Bootstrap 5
- **🔍 Search & Filtering**: Advanced search and filtering capabilities
- **📊 Reporting**: Comprehensive reporting with PDF/Excel export
- **🔔 Notifications**: SMS and email notifications
- **👨‍💼 User Management**: Role-based access control
- **📋 Audit Trail**: Complete audit logging for compliance

## 🛠️ Technology Stack

- **Backend**: Django 5.2.3, Python 3.11+
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Bootstrap 5, jQuery, Chart.js
- **Caching**: Redis
- **Task Queue**: Celery
- **Web Server**: Nginx + Gunicorn
- **Containerization**: Docker & Docker Compose

## 📋 Requirements

- Python 3.11+
- PostgreSQL 13+ (for production)
- Redis 6+ (for caching and task queue)

## 🚀 Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd golam
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main application: http://localhost:8000
   - Admin interface: http://localhost:8000/admin

### Production Deployment

#### Using Docker Compose (Recommended)

1. **Clone and configure**
   ```bash
   git clone <repository-url>
   cd golam
   cp .env.example .env
   # Edit .env with production settings
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Run initial setup**
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   docker-compose exec web python manage.py collectstatic --noinput
   ```

#### Manual Deployment

1. **Use the deployment script**
   ```bash
   python deploy.py --environment production
   ```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Environment
ENVIRONMENT=production
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/microfinance_db

# Cache
REDIS_URL=redis://localhost:6379/1

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m security

# Run with coverage
pytest --cov=apps --cov-report=html
```

## 🔒 Security Features

- **Authentication**: Django's built-in authentication with custom user model
- **Authorization**: Role-based access control
- **CSRF Protection**: Cross-site request forgery protection
- **SQL Injection Protection**: Parameterized queries and input validation
- **Rate Limiting**: API and login rate limiting
- **Security Headers**: Comprehensive security headers
- **Audit Logging**: Complete audit trail
- **Input Validation**: Comprehensive input sanitization

## 🔧 Management Commands

### System Health Check
```bash
python manage.py system_health_check --verbose
```

### Database Optimization
```bash
python manage.py optimize_database --create-indexes --vacuum
```

### Database Backup
```bash
python manage.py backup_database --backup
python manage.py backup_database --restore backup_file.sql
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- **Email**: admin@golamfinancial.co.tz

---

**Golam Microfinance System** - Empowering financial inclusion through technology.