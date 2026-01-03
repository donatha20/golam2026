"""
Settings package for microfinance_system.
Automatically loads the appropriate settings based on DJANGO_SETTINGS_MODULE.
"""

import os
from decouple import config

# Determine which settings to use
ENVIRONMENT = config('ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'staging':
    from .production import *
    DEBUG = True  # Enable debug for staging
else:
    from .development import *
