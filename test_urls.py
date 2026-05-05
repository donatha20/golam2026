#!/usr/bin/env python
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.repayments.views import payment_list
import re

User = get_user_model()

# Create a test request
factory = RequestFactory()
request = factory.get('/repayments/list/')

# Add a user to the request
try:
    user = User.objects.first()
    request.user = user
    request.session = {}
    
    response = payment_list(request)
    
    # Look for the action buttons in the HTML
    html = response.content.decode('utf-8')
    
    # Find the first occurrence of buttons in the table
    pattern = r'<a href="([^"]*)"[^>]*>\s*<i class="fas fa-eye[^<]*</i>View'
    view_links = re.findall(pattern, html)
    
    pattern2 = r'<a href="([^"]*)"[^>]*>\s*<i class="fas fa-undo[^<]*</i>Reverse'
    reverse_links = re.findall(pattern2, html)
    
    print("VIEW button URLs (first 3):")
    for link in view_links[:3]:
        print(f"  {link}")
    
    print("\nREVERSE button URLs (first 3):")
    for link in reverse_links[:3]:
        print(f"  {link}")
    
    print("\nTotal VIEW buttons:", len(view_links))
    print("Total REVERSE buttons:", len(reverse_links))
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
