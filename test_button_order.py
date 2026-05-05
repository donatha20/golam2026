#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.repayments.views import payment_list
import re

User = get_user_model()
factory = RequestFactory()
request = factory.get('/repayments/list/')
user = User.objects.first()
request.user = user
request.session = {}

response = payment_list(request)
html = response.content.decode('utf-8')

# Find the table body
tbody_match = re.search(r'<tbody>(.*?)</tbody>', html, re.DOTALL)
if tbody_match:
    tbody = tbody_match.group(1)
    
    # Split by <tr> to find rows
    rows = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL)
    
    print(f"Found {len(rows)} rows in table\n")
    
    # Look at the first 3 rows for action buttons
    for i, row in enumerate(rows[:3]):
        if 'payment_detail' in row or 'reverse_payment' in row:
            print(f"Row {i}:")
            # Extract button links
            links = re.findall(r'<a href="([^"]*)"[^>]*>([^<]*<i[^<]*</i>[^<]*|[^<]*)</a>', row)
            for link, label in links:
                if 'payment' in link or 'reverse' in link:
                    print(f"  {link.strip()} - Label contains: {label.strip()[:30]}")
            print()
