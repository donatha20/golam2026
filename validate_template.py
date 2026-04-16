#!/usr/bin/env python
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')

import django
django.setup()

from django.template.loader import get_template

try:
    template = get_template('loans/record_repayment.html')
    print("✓ Template is valid")
except Exception as e:
    print(f"✗ Template error: {e}")
    sys.exit(1)
