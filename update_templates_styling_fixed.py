#!/usr/bin/env python3
"""
Script to update loan templates with consistent styling
"""

import os
import re

def update_template_styling(template_path, template_name):
    """Update a template with consistent styling"""
    
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # CSS styles to add
    css_styles = """
    /* Compact Stats Cards */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.3s ease;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .stat-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.25rem;
    }
    
    .stat-change {
        font-size: 0.7rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .stat-positive { color: #16a34a; }
    .stat-negative { color: #dc2626; }
    .stat-warning { color: #d97706; }
    
    /* Action Buttons Grid */
    .action-buttons-section {
        margin-bottom: 2rem;
    }
    
    .action-buttons-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
    }
    
    .action-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        text-decoration: none;
        color: #374151;
        transition: all 0.3s ease;
        min-height: 100px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .action-btn:hover {
        background: linear-gradient(135deg, #2b7a76 0%, #0d9488 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(43, 122, 118, 0.3);
        text-decoration: none;
    }
    
    .action-btn i {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }
    
    .action-btn span {
        font-size: 0.85rem;
        font-weight: 600;
        text-align: center;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .stats-grid {
            grid-template-columns: 1fr;
            gap: 0.5rem;
        }
        
        .stat-card {
            padding: 0.75rem;
            min-height: 80px;
        }
        
        .stat-value {
            font-size: 1.25rem;
        }
        
        .stat-title {
            font-size: 0.7rem;
        }
        
        .action-buttons-grid {
            grid-template-columns: 1fr;
        }
        
        .action-btn {
            padding: 0.875rem;
            min-height: 80px;
        }
    }
"""
    
    # Check if template already has our CSS
    if "/* Compact Stats Cards */" in content:
        print(f"Template {template_name} already has our CSS styling")
        return
    
    # Find where to insert CSS - look for existing CSS block first
    css_block_pattern = r'({%\s*block\s+extra_css\s*%})(.*?)({%\s*endblock\s*%})'
    css_match = re.search(css_block_pattern, content, re.DOTALL)
    
    if css_match:
        # Update existing CSS block
        existing_css = css_match.group(2).strip()
        new_css_content = css_match.group(1) + "\n<style>\n" + css_styles + "\n</style>\n"
        if existing_css:
            new_css_content += existing_css + "\n"
        new_css_content += css_match.group(3)
        content = content.replace(css_match.group(0), new_css_content)
    else:
        # Add new CSS block after title block or at the beginning
        title_pattern = r'({%\s*block\s+title\s*%}.*?{%\s*endblock\s*%})'
        title_match = re.search(title_pattern, content, re.DOTALL)
        if title_match:
            css_block = f"\n\n{{% block extra_css %}}\n<style>\n{css_styles}\n</style>\n{{% endblock %}}\n"
            content = content.replace(title_match.group(0), title_match.group(0) + css_block)
        else:
            # Insert after extends block
            extends_pattern = r'({%\s*extends\s*["\'][^"\']+["\']\s*%})'
            extends_match = re.search(extends_pattern, content)
            if extends_match:
                css_block = f"\n\n{{% block extra_css %}}\n<style>\n{css_styles}\n</style>\n{{% endblock %}}\n"
                content = content.replace(extends_match.group(0), extends_match.group(0) + css_block)
    
    # Write the updated content back
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated template: {template_name}")

def main():
    """Main function to update all templates"""
    base_path = "templates/loans"
    
    templates_to_update = [
        "defaulted_loans.html",
        "missed_schedules.html", 
        "missed_payments.html",
        "loan_ageing.html",
        "portfolio_at_risk.html",
        "interest_receivables.html",
        "loan_graphs.html",
        "nearing_completion.html",
        "written_off_loans.html",
        "redisbursed_loans.html",
        "rollover_payments.html"
    ]
    
    for template_name in templates_to_update:
        template_path = os.path.join(base_path, template_name)
        update_template_styling(template_path, template_name)
    
    print("Template styling updates completed!")

if __name__ == "__main__":
    main()
