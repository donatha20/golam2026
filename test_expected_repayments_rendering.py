#!/usr/bin/env python
"""Test that the expected-repayments page renders without SafeString format errors."""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from django.test import RequestFactory
from apps.loans.views import ExpectedRepaymentsView
from apps.accounts.models import CustomUser

try:
    # Find or create a test user
    user = CustomUser.objects.first()
    if not user:
        print("No users found in database")
        sys.exit(1)
    
    # Create a request
    factory = RequestFactory()
    request = factory.get('/loans/expected-repayments/')
    request.user = user
    
    # Get the view
    view = ExpectedRepaymentsView.as_view()
    response = view(request)
    
    # Try to render the response
    if hasattr(response, 'render'):
        response.render()
    
    print("✓ Expected-repayments page renders successfully!")
    print(f"✓ Status Code: {response.status_code}")
    print("✓ No SafeString format errors detected!")
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
