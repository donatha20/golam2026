"""
Management command to create default payroll data.
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from apps.payroll.models import Department, Position, AllowanceType, DeductionType


class Command(BaseCommand):
    help = 'Create default payroll data (departments, positions, allowance types, deduction types)'

    def handle(self, *args, **options):
        self.stdout.write('Creating default payroll data...')
        
        # Create default departments
        self.create_departments()
        
        # Create default allowance types
        self.create_allowance_types()
        
        # Create default deduction types
        self.create_deduction_types()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created default payroll data')
        )

    def create_departments(self):
        """Create default departments."""
        departments = [
            {
                'name': 'Human Resources',
                'code': 'HR',
                'description': 'Human Resources and Administration'
            },
            {
                'name': 'Finance',
                'code': 'FIN',
                'description': 'Finance and Accounting'
            },
            {
                'name': 'Operations',
                'code': 'OPS',
                'description': 'Operations and Field Work'
            },
            {
                'name': 'Information Technology',
                'code': 'IT',
                'description': 'Information Technology and Systems'
            },
            {
                'name': 'Customer Service',
                'code': 'CS',
                'description': 'Customer Service and Support'
            },
            {
                'name': 'Credit',
                'code': 'CRD',
                'description': 'Credit Analysis and Risk Management'
            },
            {
                'name': 'Collections',
                'code': 'COL',
                'description': 'Loan Collections and Recovery'
            },
        ]
        
        for dept_data in departments:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults=dept_data
            )
            if created:
                self.stdout.write(f'Created department: {dept.name}')
            
            # Create positions for each department
            self.create_positions_for_department(dept)

    def create_positions_for_department(self, department):
        """Create default positions for a department."""
        positions_map = {
            'HR': [
                {'title': 'HR Manager', 'grade': 'M1', 'min_salary': 800000, 'max_salary': 1200000},
                {'title': 'HR Officer', 'grade': 'O1', 'min_salary': 500000, 'max_salary': 700000},
                {'title': 'HR Assistant', 'grade': 'A1', 'min_salary': 300000, 'max_salary': 450000},
            ],
            'FIN': [
                {'title': 'Finance Manager', 'grade': 'M1', 'min_salary': 1000000, 'max_salary': 1500000},
                {'title': 'Accountant', 'grade': 'O1', 'min_salary': 600000, 'max_salary': 900000},
                {'title': 'Finance Officer', 'grade': 'O2', 'min_salary': 500000, 'max_salary': 700000},
                {'title': 'Cashier', 'grade': 'A1', 'min_salary': 350000, 'max_salary': 500000},
            ],
            'OPS': [
                {'title': 'Operations Manager', 'grade': 'M1', 'min_salary': 900000, 'max_salary': 1300000},
                {'title': 'Branch Manager', 'grade': 'M2', 'min_salary': 700000, 'max_salary': 1000000},
                {'title': 'Field Officer', 'grade': 'O1', 'min_salary': 400000, 'max_salary': 600000},
                {'title': 'Customer Relations Officer', 'grade': 'O2', 'min_salary': 450000, 'max_salary': 650000},
            ],
            'IT': [
                {'title': 'IT Manager', 'grade': 'M1', 'min_salary': 1200000, 'max_salary': 1800000},
                {'title': 'Software Developer', 'grade': 'O1', 'min_salary': 800000, 'max_salary': 1200000},
                {'title': 'IT Support Specialist', 'grade': 'O2', 'min_salary': 500000, 'max_salary': 750000},
                {'title': 'System Administrator', 'grade': 'O1', 'min_salary': 700000, 'max_salary': 1000000},
            ],
            'CS': [
                {'title': 'Customer Service Manager', 'grade': 'M2', 'min_salary': 600000, 'max_salary': 900000},
                {'title': 'Customer Service Representative', 'grade': 'O2', 'min_salary': 350000, 'max_salary': 500000},
                {'title': 'Call Center Agent', 'grade': 'A1', 'min_salary': 300000, 'max_salary': 400000},
            ],
            'CRD': [
                {'title': 'Credit Manager', 'grade': 'M1', 'min_salary': 900000, 'max_salary': 1400000},
                {'title': 'Credit Analyst', 'grade': 'O1', 'min_salary': 600000, 'max_salary': 850000},
                {'title': 'Loan Officer', 'grade': 'O2', 'min_salary': 500000, 'max_salary': 700000},
                {'title': 'Risk Officer', 'grade': 'O1', 'min_salary': 650000, 'max_salary': 900000},
            ],
            'COL': [
                {'title': 'Collections Manager', 'grade': 'M2', 'min_salary': 700000, 'max_salary': 1000000},
                {'title': 'Collections Officer', 'grade': 'O2', 'min_salary': 450000, 'max_salary': 650000},
                {'title': 'Field Collections Agent', 'grade': 'A1', 'min_salary': 350000, 'max_salary': 500000},
            ],
        }
        
        if department.code in positions_map:
            for pos_data in positions_map[department.code]:
                pos_data['department'] = department
                pos_data['minimum_salary'] = Decimal(str(pos_data.pop('min_salary')))
                pos_data['maximum_salary'] = Decimal(str(pos_data.pop('max_salary')))
                
                position, created = Position.objects.get_or_create(
                    title=pos_data['title'],
                    department=department,
                    defaults=pos_data
                )
                if created:
                    self.stdout.write(f'Created position: {position.title} in {department.name}')

    def create_allowance_types(self):
        """Create default allowance types."""
        allowances = [
            {
                'name': 'Transport Allowance',
                'code': 'TRANS',
                'description': 'Monthly transport allowance',
                'calculation_type': 'fixed',
                'default_amount': Decimal('50000.00'),
                'is_taxable': True,
            },
            {
                'name': 'Housing Allowance',
                'code': 'HOUSE',
                'description': 'Monthly housing allowance',
                'calculation_type': 'percentage',
                'default_amount': Decimal('20.00'),  # 20% of basic salary
                'is_taxable': True,
            },
            {
                'name': 'Meal Allowance',
                'code': 'MEAL',
                'description': 'Daily meal allowance',
                'calculation_type': 'fixed',
                'default_amount': Decimal('15000.00'),
                'is_taxable': False,
            },
            {
                'name': 'Medical Allowance',
                'code': 'MED',
                'description': 'Monthly medical allowance',
                'calculation_type': 'fixed',
                'default_amount': Decimal('30000.00'),
                'is_taxable': False,
            },
            {
                'name': 'Performance Allowance',
                'code': 'PERF',
                'description': 'Performance-based allowance',
                'calculation_type': 'variable',
                'default_amount': Decimal('0.00'),
                'is_taxable': True,
            },
            {
                'name': 'Overtime Allowance',
                'code': 'OT',
                'description': 'Overtime payment allowance',
                'calculation_type': 'variable',
                'default_amount': Decimal('0.00'),
                'is_taxable': True,
            },
            {
                'name': 'Phone Allowance',
                'code': 'PHONE',
                'description': 'Mobile phone allowance',
                'calculation_type': 'fixed',
                'default_amount': Decimal('20000.00'),
                'is_taxable': True,
            },
            {
                'name': 'Fuel Allowance',
                'code': 'FUEL',
                'description': 'Fuel allowance for company vehicle users',
                'calculation_type': 'fixed',
                'default_amount': Decimal('100000.00'),
                'is_taxable': True,
            },
        ]
        
        for allowance_data in allowances:
            allowance, created = AllowanceType.objects.get_or_create(
                code=allowance_data['code'],
                defaults=allowance_data
            )
            if created:
                self.stdout.write(f'Created allowance type: {allowance.name}')

    def create_deduction_types(self):
        """Create default deduction types."""
        deductions = [
            {
                'name': 'Pay As You Earn (PAYE)',
                'code': 'PAYE',
                'description': 'Income tax deduction',
                'calculation_type': 'variable',
                'default_amount': Decimal('0.00'),
                'is_statutory': True,
            },
            {
                'name': 'NSSF Contribution',
                'code': 'NSSF',
                'description': 'National Social Security Fund contribution',
                'calculation_type': 'percentage',
                'default_amount': Decimal('5.00'),  # 5% of basic salary
                'is_statutory': True,
            },
            {
                'name': 'NHIF Contribution',
                'code': 'NHIF',
                'description': 'National Health Insurance Fund contribution',
                'calculation_type': 'variable',
                'default_amount': Decimal('0.00'),
                'is_statutory': True,
            },
            {
                'name': 'WCF Contribution',
                'code': 'WCF',
                'description': 'Workers Compensation Fund contribution',
                'calculation_type': 'percentage',
                'default_amount': Decimal('0.50'),  # 0.5% of gross salary
                'is_statutory': True,
            },
            {
                'name': 'SDL Contribution',
                'code': 'SDL',
                'description': 'Skills Development Levy contribution',
                'calculation_type': 'percentage',
                'default_amount': Decimal('0.50'),  # 0.5% of gross salary
                'is_statutory': True,
            },
            {
                'name': 'Salary Advance',
                'code': 'ADV',
                'description': 'Salary advance repayment',
                'calculation_type': 'variable',
                'default_amount': Decimal('0.00'),
                'is_statutory': False,
            },
            {
                'name': 'Loan Repayment',
                'code': 'LOAN',
                'description': 'Employee loan repayment',
                'calculation_type': 'variable',
                'default_amount': Decimal('0.00'),
                'is_statutory': False,
            },
            {
                'name': 'Disciplinary Fine',
                'code': 'FINE',
                'description': 'Disciplinary fine deduction',
                'calculation_type': 'fixed',
                'default_amount': Decimal('0.00'),
                'is_statutory': False,
            },
            {
                'name': 'Uniform Deduction',
                'code': 'UNIFORM',
                'description': 'Company uniform cost deduction',
                'calculation_type': 'fixed',
                'default_amount': Decimal('25000.00'),
                'is_statutory': False,
            },
            {
                'name': 'Training Fee',
                'code': 'TRAIN',
                'description': 'Training and development fee',
                'calculation_type': 'fixed',
                'default_amount': Decimal('0.00'),
                'is_statutory': False,
            },
        ]
        
        for deduction_data in deductions:
            deduction, created = DeductionType.objects.get_or_create(
                code=deduction_data['code'],
                defaults=deduction_data
            )
            if created:
                self.stdout.write(f'Created deduction type: {deduction.name}')
