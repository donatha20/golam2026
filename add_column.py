import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microfinance_system.settings')
django.setup()

from django.db import connection

# Add the external_reference column to the Payment table
with connection.cursor() as cursor:
    try:
        cursor.execute("ALTER TABLE repayments_payment ADD COLUMN external_reference VARCHAR(100);")
        print("Successfully added external_reference column")
    except Exception as e:
        print(f"Error: {e}")
        # Check if column already exists
        cursor.execute("PRAGMA table_info(repayments_payment);")
        columns = cursor.fetchall()
        print("Current columns:")
        for col in columns:
            print(f"  {col[1]} - {col[2]}")
