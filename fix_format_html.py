#!/usr/bin/env python
"""Fix all format_html calls to use pre-formatted strings instead of format codes."""

import re

# Read the file
with open('apps/loans/tables.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences of format_html with {:,.2f} to use pre-formatted strings
# Pattern 1: '<span class="X">Tsh {:,.2f}</span>'
pattern1 = r"format_html\(\s*'<span class=\"([^\"]+)\">Tsh \{:,\.2f\}</span>',\s*(\w+)\s*\)"
replacement1 = r"format_html('<span class=\"\1\">Tsh {}</span>', \"{:,.2f}\".format(\2))"
content = re.sub(pattern1, replacement1, content)

# Pattern 2: '<span class="X npl-amount">Tsh {:,.2f}</span>'
pattern2 = r"format_html\(\s*'<span class=\"([^\"]+) ([^\"]+)\">Tsh \{:,\.2f\}</span>',\s*(\w+)\s*\)"
replacement2 = r"format_html('<span class=\"\1 \2\">Tsh {}</span>', \"{:,.2f}\".format(\3))"
content = re.sub(pattern2, replacement2, content)

# Write back
with open('apps/loans/tables.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed all format_html format code issues")
