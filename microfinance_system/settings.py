"""
Django settings for microfinance_system project.

This file imports the appropriate settings based on the ENVIRONMENT variable.
For production deployment, use the settings package structure.
"""

import os
from decouple import config

# Determine which settings to use
ENVIRONMENT = config('ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .settings.production import *
elif ENVIRONMENT == 'staging':
    from .settings.production import *
    DEBUG = True  # Enable debug for staging
else:
    from .settings.development import *




