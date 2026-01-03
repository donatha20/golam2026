#!/usr/bin/env python3
"""
Script to update loan template styling for consistency
Applies compact card design and uniform action buttons across all loan management templates
"""

import os
import re

# Standard CSS for all templates
STANDARD_CSS = '''    /* Universal System Styles */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .stat-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 12px;
        padding: 1rem;
        min-height: 120px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .stat-card:hover {
        box-shadow: 0 4px 20px rgba(43, 122, 118, 0.15);
        transform: translateY(-2px);
        border-color: #2b7a76;
    }

    .stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #2b7a76 0%, #34d399 100%);
        transition: width 0.3s ease;
    }

    .stat-card:hover::before {
        width: 6px;
    }

    .stat-card.risk-high::before {
        background: linear-gradient(180deg, #dc2626 0%, #ef4444 100%);
    }

    .stat-card.risk-medium::before {
        background: linear-gradient(180deg, #f59e0b 0%, #fbbf24 100%);
    }

    .stat-card.risk-low::before {
        background: linear-gradient(180deg, #16a34a 0%, #22c55e 100%);
    }

    .stat-title {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.5rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.25rem;
        line-height: 1.2;
    }

    .stat-change {
        font-size: 0.7rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .stat-positive {
        color: #16a34a;
    }

    .stat-warning {
        color: #f59e0b;
    }

    .stat-danger {
        color: #dc2626;
    }

    /* Action Buttons Grid */
    .action-buttons-section {
        margin-bottom: 2rem;
    }

    .action-buttons-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }

    .action-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1rem;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        text-decoration: none;
        color: #475569;
        transition: all 0.3s ease;
        text-align: center;
        min-height: 100px;
        justify-content: center;
    }

    .action-btn i {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
        transition: transform 0.3s ease;
    }

    .action-btn-primary {
        border-color: #2b7a76;
        color: #2b7a76;
    }

    .action-btn-primary:hover {
        background: linear-gradient(135deg, #2b7a76 0%, #34d399 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(43, 122, 118, 0.3);
    }

    .action-btn-success {
        border-color: #16a34a;
        color: #16a34a;
    }

    .action-btn-success:hover {
        background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(22, 163, 74, 0.3);
    }

    .action-btn-danger {
        border-color: #dc2626;
        color: #dc2626;
    }

    .action-btn-danger:hover {
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(220, 38, 38, 0.3);
    }

    .action-btn-warning {
        border-color: #f59e0b;
        color: #f59e0b;
    }

    .action-btn-warning:hover {
        background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3);
    }

    .action-btn-outline {
        border-color: #64748b;
        color: #64748b;
    }

    .action-btn-outline:hover {
        background: linear-gradient(135deg, #64748b 0%, #94a3b8 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(100, 116, 139, 0.3);
    }

    .action-btn:hover i {
        transform: scale(1.1);
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .stats-grid {
            grid-template-columns: 1fr;
            gap: 0.5rem;
        }
        
        .stat-card {
            padding: 0.75rem;
            min-height: 100px;
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
            padding: 0.875rem 1rem;
            min-height: 80px;
        }
    }'''

# Templates to update
TEMPLATES = [
    'defaulted_loans.html',
    'loans_ageing.html',
    'portfolio_at_risk.html',
    'interest_receivables.html',
    'loans_graphs_summary.html',
    'nearing_completion.html',
    'written_off_loans.html',
    'redisbursed_loans.html',
    'rollover_payments.html',
    'missed_schedules.html',
    'missed_payments.html'
]

def update_template(template_path):
    """Update a single template with consistent styling"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and replace the styles section
        style_pattern = r'{% block extra_css %}.*?</style>'
        
        if re.search(style_pattern, content, re.DOTALL):
            # Replace existing styles
            new_content = re.sub(
                style_pattern,
                f'{% block extra_css %}\n<style>\n{STANDARD_CSS}\n</style>',
                content,
                flags=re.DOTALL
            )
        else:
            # Add styles if not present
            new_content = content.replace(
                '{% block content %}',
                f'{% block extra_css %}\n<style>\n{STANDARD_CSS}\n</style>\n{% endblock %}\n\n{% block content %}'
            )
        
        # Update stats grid HTML pattern
        stats_pattern = r'<div class="stats-grid">.*?</div>'
        if re.search(stats_pattern, new_content, re.DOTALL):
            # Ensure stat cards don't have old class names
            new_content = re.sub(r'class="stat-card[^"]*"', 'class="stat-card"', new_content)
        
        # Update action buttons if present
        action_pattern = r'<div[^>]*class="[^"]*action[^"]*"[^>]*>.*?</div>'
        if re.search(action_pattern, new_content, re.DOTALL):
            print(f"Found action section in {template_path}")
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error updating {template_path}: {e}")
        return False

def main():
    """Main function to update all templates"""
    base_path = "e:\\New folder\\golam\\templates\\loans"
    updated = 0
    failed = 0
    
    for template in TEMPLATES:
        template_path = os.path.join(base_path, template)
        if os.path.exists(template_path):
            if update_template(template_path):
                print(f"✓ Updated {template}")
                updated += 1
            else:
                print(f"✗ Failed to update {template}")
                failed += 1
        else:
            print(f"! Template not found: {template}")
    
    print(f"\nSummary: {updated} updated, {failed} failed")

if __name__ == "__main__":
    main()
