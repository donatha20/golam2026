#!/usr/bin/env python
"""
Script to add Main branch to the database.
Run this script from the project root directory.
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.accounts.models import Branch

def add_main_branch():
    """Add Main branch to the database if it doesn't exist."""
    try:
        # Check if Main branch already exists
        branch, created = Branch.objects.get_or_create(
            name='Main Branch',
            defaults={
                'code': 'MAIN',
                'address': 'Head Office, Main Street, City Center',
                'phone_number': '+255123456789',
                'email': 'main@golamfinancial.co.tz',
                'is_active': True
            }
        )
        
        if created:
            print("✅ Main Branch created successfully!")
            print(f"   Name: {branch.name}")
            print(f"   Code: {branch.code}")
            print(f"   Address: {branch.address}")
            print(f"   Phone: {branch.phone_number}")
            print(f"   Email: {branch.email}")
        else:
            print("ℹ️  Main Branch already exists in the database.")
            print(f"   Name: {branch.name}")
            print(f"   Code: {branch.code}")
            
    except Exception as e:
        print(f"❌ Error creating Main Branch: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Adding Main Branch to the database...")
    print("-" * 40)
    
    success = add_main_branch()
    
    print("-" * 40)
    if success:
        print("Script completed successfully!")
    else:
        print("Script completed with errors.")
