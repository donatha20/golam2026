"""
Script to update all superusers to have admin role.
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from apps.accounts.models import CustomUser, UserRole


def update_superusers_to_admin():
    """Update all superusers to have admin role."""
    superusers = CustomUser.objects.filter(is_superuser=True)
    
    print(f"Found {superusers.count()} superuser(s)")
    
    updated_count = 0
    for user in superusers:
        if user.role != UserRole.ADMIN:
            print(f"Updating {user.username} ({user.get_full_name()}) to admin role")
            user.role = UserRole.ADMIN
            user.save()
            updated_count += 1
        else:
            print(f"{user.username} already has admin role")
    
    print(f"\nUpdated {updated_count} user(s) to admin role")
    print("Done!")


if __name__ == '__main__':
    update_superusers_to_admin()
