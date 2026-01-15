#!/usr/bin/env python3
"""
Template Optimization Script for Golam Financial Services
This script applies consistent sizing and styling classes across all templates.
"""

import os
import re
from pathlib import Path

# Define the project root
PROJECT_ROOT = Path(__file__).parent

# Template directories to process
TEMPLATE_DIRS = [
    'templates',
    'templates/loans',
    'templates/borrowers', 
    'templates/repayments',
    'templates/savings',
    'templates/assets',
    'templates/sms',
    'templates/accounts',
    'templates/core',
    'templates/finance_tracker',
    'templates/financial_statements',
    'templates/settings',
    'templates/users',
    'templates/analytics',
    'templates/registration',
    'templates/system'
]

# CSS class mappings for optimization
CLASS_MAPPINGS = {
    # Table optimizations
    r'class="table table-striped table-hover"': 'class="table table-striped table-hover table-sm"',
    r'class="table table-striped"': 'class="table table-striped table-sm"',
    r'class="table table-hover"': 'class="table table-hover table-sm"',
    r'class="table"': 'class="table table-sm"',
    
    # Button optimizations
    r'class="btn btn-primary"': 'class="btn btn-primary btn-sm"',
    r'class="btn btn-secondary"': 'class="btn btn-secondary btn-sm"',
    r'class="btn btn-success"': 'class="btn btn-success btn-sm"',
    r'class="btn btn-danger"': 'class="btn btn-danger btn-sm"',
    r'class="btn btn-warning"': 'class="btn btn-warning btn-sm"',
    r'class="btn btn-info"': 'class="btn btn-info btn-sm"',
    
    # Form control optimizations
    r'class="form-control"': 'class="form-control form-control-sm"',
    r'class="form-select"': 'class="form-select form-select-sm"',
    
    # Card optimizations
    r'class="card-body"': 'class="card-body p-compact"',
    r'class="card-header"': 'class="card-header py-compact"',
    
    # Spacing optimizations
    r'class="mb-4"': 'class="mb-compact"',
    r'class="mt-4"': 'class="mt-compact"',
    r'class="my-4"': 'class="my-compact"',
    
    # Container optimizations
    r'<div class="container">': '<div class="container-fluid px-compact">',
    r'<div class="row mb-3">': '<div class="row mb-compact">',
}

# Inline style optimizations
STYLE_OPTIMIZATIONS = {
    # Font size reductions
    r'font-size:\s*16px': 'font-size: 14px',
    r'font-size:\s*15px': 'font-size: 13px',
    r'font-size:\s*14px': 'font-size: 12px',
    r'font-size:\s*1\.2rem': 'font-size: 1rem',
    r'font-size:\s*1\.1rem': 'font-size: 0.95rem',
    
    # Padding reductions
    r'padding:\s*20px': 'padding: 16px',
    r'padding:\s*1\.5rem': 'padding: 1rem',
    r'padding:\s*24px': 'padding: 16px',
    
    # Margin reductions
    r'margin-bottom:\s*24px': 'margin-bottom: 16px',
    r'margin-bottom:\s*1\.5rem': 'margin-bottom: 1rem',
    r'margin-top:\s*24px': 'margin-top: 16px',
    r'margin-top:\s*1\.5rem': 'margin-top: 1rem',
}

def optimize_template_file(file_path):
    """Optimize a single template file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Apply class mappings
        for old_class, new_class in CLASS_MAPPINGS.items():
            if re.search(old_class, content):
                content = re.sub(old_class, new_class, content)
                changes_made.append(f"Updated class: {old_class} -> {new_class}")
        
        # Apply style optimizations
        for old_style, new_style in STYLE_OPTIMIZATIONS.items():
            if re.search(old_style, content, re.IGNORECASE):
                content = re.sub(old_style, new_style, content, flags=re.IGNORECASE)
                changes_made.append(f"Optimized style: {old_style} -> {new_style}")
        
        # Add compact utility classes to common patterns
        # Tables
        if 'table-container' in content and 'table-sm' not in content:
            content = content.replace('class="table table-striped"', 'class="table table-striped table-sm"')
            changes_made.append("Added table-sm to tables")
        
        # Forms
        if 'form-control' in content and 'form-control-sm' not in content:
            content = re.sub(r'class="form-control"(?!\s*form-control-sm)', 'class="form-control form-control-sm"', content)
            changes_made.append("Added form-control-sm to inputs")
        
        # Buttons in table actions
        if 'btn-sm' not in content and ('Edit' in content or 'Delete' in content or 'View' in content):
            content = re.sub(r'class="btn (btn-\w+)"(?!\s*btn-sm)', r'class="btn \1 btn-sm"', content)
            changes_made.append("Added btn-sm to action buttons")
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_made
        
        return []
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def optimize_all_templates():
    """Optimize all templates in the project."""
    total_files_processed = 0
    total_changes_made = 0
    
    print("🚀 Starting template optimization...")
    print("=" * 60)
    
    for template_dir in TEMPLATE_DIRS:
        dir_path = PROJECT_ROOT / template_dir
        
        if not dir_path.exists():
            continue
            
        print(f"\n📁 Processing directory: {template_dir}")
        
        # Find all HTML files
        html_files = list(dir_path.glob('*.html'))
        
        for html_file in html_files:
            changes = optimize_template_file(html_file)
            total_files_processed += 1
            
            if changes:
                total_changes_made += len(changes)
                print(f"  ✅ {html_file.name}: {len(changes)} optimizations")
                for change in changes[:3]:  # Show first 3 changes
                    print(f"    • {change}")
                if len(changes) > 3:
                    print(f"    • ... and {len(changes) - 3} more")
            else:
                print(f"  ℹ️  {html_file.name}: already optimized")
    
    print("\n" + "=" * 60)
    print(f"🎉 Optimization complete!")
    print(f"📊 Files processed: {total_files_processed}")
    print(f"🔧 Total optimizations: {total_changes_made}")
    print("\n💡 Benefits of these optimizations:")
    print("   • Reduced font sizes for better space utilization")
    print("   • Compact form controls and buttons")
    print("   • Consistent spacing throughout the application")
    print("   • Improved mobile responsiveness")
    print("   • Better visual hierarchy")

def create_template_snippet_library():
    """Create a library of optimized template snippets."""
    snippets = {
        "optimized_table": '''
<!-- Optimized Table Template -->
<div class="table-container">
    <table class="table table-striped table-hover table-sm">
        <thead>
            <tr>
                <th>Column 1</th>
                <th>Column 2</th>
                <th class="text-center">Actions</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Data 1</td>
                <td>Data 2</td>
                <td class="text-center">
                    <a href="#" class="btn btn-primary btn-sm btn-action">
                        <i class="fas fa-edit"></i> Edit
                    </a>
                    <a href="#" class="btn btn-danger btn-sm btn-action">
                        <i class="fas fa-trash"></i> Delete
                    </a>
                </td>
            </tr>
        </tbody>
    </table>
</div>
        ''',
        
        "optimized_form": '''
<!-- Optimized Form Template -->
<form class="needs-validation" novalidate>
    <div class="row mb-compact">
        <div class="col-md-6">
            <label for="field1" class="form-label">Field 1</label>
            <input type="text" class="form-control form-control-sm" id="field1" required>
        </div>
        <div class="col-md-6">
            <label for="field2" class="form-label">Field 2</label>
            <select class="form-select form-select-sm" id="field2" required>
                <option value="">Choose...</option>
                <option value="1">Option 1</option>
            </select>
        </div>
    </div>
    <div class="row">
        <div class="col-12">
            <button type="submit" class="btn btn-primary btn-sm">
                <i class="fas fa-save"></i> Save
            </button>
            <button type="button" class="btn btn-secondary btn-sm">
                <i class="fas fa-times"></i> Cancel
            </button>
        </div>
    </div>
</form>
        ''',
        
        "optimized_card": '''
<!-- Optimized Card Template -->
<div class="card shadow-sm-primary">
    <div class="card-header py-compact">
        <h5 class="card-title mb-0">
            <i class="fas fa-icon"></i> Card Title
        </h5>
    </div>
    <div class="card-body p-compact">
        <p class="text-muted-compact">Card content goes here.</p>
        <div class="d-flex gap-2">
            <button class="btn btn-primary btn-sm">Action 1</button>
            <button class="btn btn-secondary btn-sm">Action 2</button>
        </div>
    </div>
</div>
        '''
    }
    
    # Save snippets to file
    snippets_file = PROJECT_ROOT / 'template_snippets.html'
    with open(snippets_file, 'w', encoding='utf-8') as f:
        f.write("<!-- Optimized Template Snippets for Golam Financial Services -->\n")
        f.write("<!-- Use these snippets as reference for consistent styling -->\n\n")
        
        for name, snippet in snippets.items():
            f.write(f"<!-- {name.upper()} -->\n")
            f.write(snippet.strip())
            f.write("\n\n")
    
    print(f"📚 Template snippet library created: {snippets_file}")

if __name__ == "__main__":
    optimize_all_templates()
    create_template_snippet_library()
    
    print("\n🎯 Next steps:")
    print("1. Review the changes in your templates")
    print("2. Test the application to ensure everything works correctly")
    print("3. Use the global-sizing.css classes in new templates")
    print("4. Refer to template_snippets.html for optimized patterns")
