"""
Development settings for microfinance_system project.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'golam_db',
        'USER': 'golam_admin',
        'PASSWORD': 'donatha@98M',
        'HOST': 'localhost',
        'PORT': '15432',
    }
}

# Email Configuration for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Admin Email for Development
ADMINS = [
    ('Golam Admin', 'admin@golamfinancial.co.tz'),
]

# Development specific settings
AUTO_APPROVE_USERS = True  # Set to True for testing

# Add debug toolbar for development
#try:
#    ##import debug_toolbar
#    INSTALLED_APPS += [
#        'debug_toolbar',
#    ]
#
 #   MIDDLEWARE += [
#       'debug_toolbar.middleware.DebugToolbarMiddleware',
 #   ]
#except ImportError:
    # Debug toolbar not installed, skip
 #   pass

# Debug toolbar configuration
#INTERNAL_IPS = [
#    '127.0.0.1',
 #   'localhost',
#]

# Logging Configuration for Development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'microfinance_dev.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'microfinance_system': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
logs_dir = BASE_DIR / 'logs'
if not logs_dir.exists():
    logs_dir.mkdir(exist_ok=True)

# Development cache (simple local memory)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Disable security features for development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
