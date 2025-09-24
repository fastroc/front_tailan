"""
Financial Rules Demo Data Generator

This script creates sample financial rules and test data to demonstrate 
the capabilities of the financial rules system.

Usage:
    python manage.py shell -c "exec(open('financial_rules/create_demo_data.py').read())"
    
Or from Django shell:
    exec(open('financial_rules/create_demo_data.py').read())
"""

import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    django.setup()

from financial_rules.models import BaseFinancialRule, RuleCondition, RuleAction
from company.models import Company

def create_demo_companies():
    """Create demo companies if they don't exist"""
    companies = []
    
    company_data = [
        {
            'name': 'TechCorp Solutions',
            'description': 'Technology consulting company',
        },
        {
            'name': 'BuildRight Construction',
            'description': 'General construction and contracting',
        },
        {
            'name': 'Green Energy LLC',
            'description': 'Renewable energy solutions',
        }
    ]
    
    for data in company_data:
        company, created = Company.objects.get_or_create(
            name=data['name'],
            defaults=data
        )
        companies.append(company)
        if created:
            print(f"✓ Created company: {company.name}")
        else:
            print(f"- Company exists: {company.name}")
    
    return companies


def create_loan_payment_rules(companies):
    """Create sample loan payment rules"""
    print("\n=== Creating Loan Payment Rules ===")
    
    for company in companies:
        # Main loan payment rule
        rule, created = BaseFinancialRule.objects.get_or_create(
            name=f"{company.name} - Loan Payment Processing",
            company=company,
            defaults={
                'description': f'Automatically split loan payments for {company.name} according to priority: Late Fees → Interest → Principal',
                'rule_type': 'loan_payment',
                'priority': 1,
                'is_active': True,
                'condition_logic': 'and'
            }
        )
        
        if created:
            print(f"✓ Created rule: {rule.name}")
            
            # Add conditions for loan payment detection
            conditions = [
                {
                    'field': 'description',
                    'operator': 'contains',
                    'value': 'loan payment',
                    'case_sensitive': False
                },
                {
                    'field': 'amount',
                    'operator': 'gte',
                    'value': '100.00'
                }
            ]
            
            for cond_data in conditions:
                condition = RuleCondition.objects.create(
                    rule=rule,
                    **cond_data
                )
                print(f"  - Added condition: {condition.field} {condition.operator} {condition.value}")
            
            # Add actions for loan payment splits
            actions = [
                {
                    'action_type': 'allocate_percentage',
                    'target_account': '2100-Late-Fees',
                    'percentage': Decimal('10.00'),
                    'parameters': '{"priority": 1, "max_amount": 500}'
                },
                {
                    'action_type': 'allocate_percentage', 
                    'target_account': '2200-Interest-Payable',
                    'percentage': Decimal('30.00'),
                    'parameters': '{"priority": 2}'
                },
                {
                    'action_type': 'allocate_remainder',
                    'target_account': '2000-Loan-Principal',
                    'parameters': '{"priority": 3}'
                }
            ]
            
            for action_data in actions:
                action = RuleAction.objects.create(
                    rule=rule,
                    **action_data
                )
                print(f"  - Added action: {action.action_type} → {action.target_account}")
        else:
            print(f"- Rule exists: {rule.name}")


def create_contact_based_rules(companies):
    """Create sample contact-based rules"""
    print("\n=== Creating Contact-Based Rules ===")
    
    # Vendor payment rules
    vendor_rules = [
        {
            'name': 'BigBoss LLC Payments',
            'contact_patterns': ['bigboss', 'big boss', 'bb llc'],
            'account': '2500-Vendor-BigBoss',
            'description': 'Automatically categorize payments to BigBoss LLC'
        },
        {
            'name': 'Rodriguez Construction',
            'contact_patterns': ['rodriguez', 'rodriguez construction', 'r construction'],
            'account': '5200-Subcontractor-Rodriguez',
            'description': 'Payments to Rodriguez Construction subcontractor'
        },
        {
            'name': 'Office Supply Vendors',
            'contact_patterns': ['officemax', 'staples', 'office depot', 'amazon office'],
            'account': '6100-Office-Supplies',
            'description': 'Office supply purchases'
        },
        {
            'name': 'Fuel and Vehicle Expenses',
            'contact_patterns': ['shell', 'exxon', 'chevron', 'bp', 'mobil'],
            'account': '6200-Vehicle-Fuel',
            'description': 'Vehicle fuel and maintenance expenses'
        }
    ]
    
    for i, company in enumerate(companies):
        for j, vendor_data in enumerate(vendor_rules):
            rule, created = BaseFinancialRule.objects.get_or_create(
                name=f"{company.name} - {vendor_data['name']}",
                company=company,
                defaults={
                    'description': vendor_data['description'],
                    'rule_type': 'contact_based',
                    'priority': 10 + j,
                    'is_active': True,
                    'condition_logic': 'or'
                }
            )
            
            if created:
                print(f"✓ Created rule: {rule.name}")
                
                # Add contact pattern conditions
                for pattern in vendor_data['contact_patterns']:
                    condition = RuleCondition.objects.create(
                        rule=rule,
                        field='contact',
                        operator='contains',
                        value=pattern,
                        case_sensitive=False
                    )
                    print(f"  - Added condition: contact contains '{pattern}'")
                
                # Add allocation action
                action = RuleAction.objects.create(
                    rule=rule,
                    action_type='allocate_full_amount',
                    target_account=vendor_data['account'],
                    parameters='{"auto_create_account": true}'
                )
                print(f"  - Added action: allocate_full_amount → {action.target_account}")
            else:
                print(f"- Rule exists: {rule.name}")


def create_general_rules(companies):
    """Create sample general categorization rules"""
    print("\n=== Creating General Rules ===")
    
    general_rules = [
        {
            'name': 'Small Cash Transactions',
            'description': 'Categorize small cash transactions as petty cash',
            'conditions': [
                {'field': 'amount', 'operator': 'lte', 'value': '50.00'},
                {'field': 'description', 'operator': 'contains', 'value': 'cash', 'case_sensitive': False}
            ],
            'actions': [
                {'action_type': 'allocate_full_amount', 'target_account': '1200-Petty-Cash'}
            ],
            'priority': 20
        },
        {
            'name': 'Utility Payments',
            'description': 'Automatically categorize utility payments',
            'conditions': [
                {'field': 'description', 'operator': 'contains', 'value': 'electric', 'case_sensitive': False},
                {'field': 'description', 'operator': 'contains', 'value': 'water', 'case_sensitive': False},
                {'field': 'description', 'operator': 'contains', 'value': 'gas', 'case_sensitive': False},
                {'field': 'description', 'operator': 'contains', 'value': 'utility', 'case_sensitive': False}
            ],
            'actions': [
                {'action_type': 'allocate_full_amount', 'target_account': '6300-Utilities'}
            ],
            'priority': 15,
            'condition_logic': 'or'
        },
        {
            'name': 'Insurance Payments',
            'description': 'Categorize insurance premium payments',
            'conditions': [
                {'field': 'description', 'operator': 'contains', 'value': 'insurance', 'case_sensitive': False},
                {'field': 'amount', 'operator': 'gte', 'value': '200.00'}
            ],
            'actions': [
                {'action_type': 'allocate_full_amount', 'target_account': '6400-Insurance'}
            ],
            'priority': 12
        }
    ]
    
    for company in companies:
        for rule_data in general_rules:
            rule, created = BaseFinancialRule.objects.get_or_create(
                name=f"{company.name} - {rule_data['name']}",
                company=company,
                defaults={
                    'description': rule_data['description'],
                    'rule_type': 'general',
                    'priority': rule_data['priority'],
                    'is_active': True,
                    'condition_logic': rule_data.get('condition_logic', 'and')
                }
            )
            
            if created:
                print(f"✓ Created rule: {rule.name}")
                
                # Add conditions
                for cond_data in rule_data['conditions']:
                    condition = RuleCondition.objects.create(
                        rule=rule,
                        **cond_data
                    )
                    print(f"  - Added condition: {condition.field} {condition.operator} {condition.value}")
                
                # Add actions
                for action_data in rule_data['actions']:
                    action = RuleAction.objects.create(
                        rule=rule,
                        **action_data
                    )
                    print(f"  - Added action: {action.action_type} → {action.target_account}")
            else:
                print(f"- Rule exists: {rule.name}")


def create_test_scenarios():
    """Create sample test scenarios for documentation"""
    test_scenarios = [
        {
            'name': 'Loan Payment Test',
            'description': 'Test loan payment splitting hierarchy',
            'transaction': {
                'amount': 1500.00,
                'description': 'Monthly loan payment to BigBoss LLC',
                'contact': 'BigBoss LLC',
                'reference': 'CHK-001'
            },
            'expected_splits': [
                {'account': '2100-Late-Fees', 'amount': 150.00, 'percentage': 10},
                {'account': '2200-Interest-Payable', 'amount': 450.00, 'percentage': 30},
                {'account': '2000-Loan-Principal', 'amount': 900.00, 'note': 'remainder'}
            ]
        },
        {
            'name': 'Contact-Based Rule Test',
            'description': 'Test vendor recognition and categorization',
            'transaction': {
                'amount': 250.00,
                'description': 'Office supplies purchase',
                'contact': 'OfficeMax Store #123',
                'reference': 'INV-4567'
            },
            'expected_splits': [
                {'account': '6100-Office-Supplies', 'amount': 250.00, 'note': 'full amount'}
            ]
        },
        {
            'name': 'Small Cash Transaction',
            'description': 'Test petty cash categorization',
            'transaction': {
                'amount': 35.00,
                'description': 'Cash for office snacks',
                'contact': 'Petty Cash',
                'reference': 'CASH-001'
            },
            'expected_splits': [
                {'account': '1200-Petty-Cash', 'amount': 35.00, 'note': 'full amount'}
            ]
        },
        {
            'name': 'Utility Payment Test',
            'description': 'Test utility payment categorization',
            'transaction': {
                'amount': 180.50,
                'description': 'Monthly electric bill payment',
                'contact': 'City Electric Company',
                'reference': 'AUTO-PAY'
            },
            'expected_splits': [
                {'account': '6300-Utilities', 'amount': 180.50, 'note': 'full amount'}
            ]
        }
    ]
    
    return test_scenarios


def print_summary():
    """Print summary of created rules"""
    print("\n" + "="*60)
    print("FINANCIAL RULES DEMO DATA SUMMARY")
    print("="*60)
    
    companies = Company.objects.all()
    total_rules = BaseFinancialRule.objects.count()
    active_rules = BaseFinancialRule.objects.filter(is_active=True).count()
    
    print(f"Companies: {companies.count()}")
    print(f"Total Rules: {total_rules}")
    print(f"Active Rules: {active_rules}")
    
    print("\nRules by Type:")
    for rule_type in ['loan_payment', 'contact_based', 'general']:
        count = BaseFinancialRule.objects.filter(rule_type=rule_type).count()
        print(f"  {rule_type.replace('_', ' ').title()}: {count}")
    
    print("\nRules by Company:")
    for company in companies:
        count = BaseFinancialRule.objects.filter(company=company).count()
        print(f"  {company.name}: {count}")
    
    print(f"\nTotal Conditions: {RuleCondition.objects.count()}")
    print(f"Total Actions: {RuleAction.objects.count()}")
    
    print("\n" + "="*60)
    print("Demo data creation completed successfully!")
    print("="*60)


def main():
    """Main function to create all demo data"""
    print("Creating Financial Rules Demo Data...")
    print("="*60)
    
    try:
        # Create companies
        companies = create_demo_companies()
        
        # Create different types of rules
        create_loan_payment_rules(companies)
        create_contact_based_rules(companies)
        create_general_rules(companies)
        
        # Print summary
        print_summary()
        
        # Create test scenarios for documentation
        test_scenarios = create_test_scenarios()
        print(f"\nCreated {len(test_scenarios)} test scenarios for documentation")
        
        return test_scenarios
        
    except Exception as e:
        print(f"Error creating demo data: {e}")
        raise


if __name__ == '__main__':
    main()
else:
    # When executed from Django shell
    test_scenarios = main()
