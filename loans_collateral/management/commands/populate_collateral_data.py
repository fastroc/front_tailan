from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta

from loans_collateral.models import CollateralType, Collateral
from loans_core.models import LoanApplication


class Command(BaseCommand):
    help = 'Populate sample collateral data for demonstration'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Creating sample collateral types...')
            
            # Create Collateral Types
            collateral_types = [
                {
                    'name': 'Residential Property',
                    'category': 'real_estate',
                    'description': 'Single-family homes, condominiums, and residential units',
                    'max_loan_to_value': Decimal('75.00'),
                    'depreciation_rate': Decimal('2.00'),
                    'risk_level': 'low',
                    'liquidity_score': 6,
                    'requires_insurance': True,
                    'requires_professional_valuation': True,
                },
                {
                    'name': 'Commercial Property',
                    'category': 'real_estate',
                    'description': 'Office buildings, retail spaces, and commercial real estate',
                    'max_loan_to_value': Decimal('70.00'),
                    'depreciation_rate': Decimal('3.00'),
                    'risk_level': 'medium',
                    'liquidity_score': 5,
                    'requires_insurance': True,
                    'requires_professional_valuation': True,
                },
                {
                    'name': 'Passenger Vehicle',
                    'category': 'vehicle',
                    'description': 'Cars, SUVs, and personal vehicles',
                    'max_loan_to_value': Decimal('80.00'),
                    'depreciation_rate': Decimal('15.00'),
                    'risk_level': 'medium',
                    'liquidity_score': 8,
                    'requires_insurance': True,
                    'requires_professional_valuation': False,
                },
                {
                    'name': 'Commercial Vehicle',
                    'category': 'vehicle',
                    'description': 'Trucks, vans, and commercial vehicles',
                    'max_loan_to_value': Decimal('75.00'),
                    'depreciation_rate': Decimal('12.00'),
                    'risk_level': 'medium',
                    'liquidity_score': 7,
                    'requires_insurance': True,
                    'requires_professional_valuation': True,
                },
                {
                    'name': 'Manufacturing Equipment',
                    'category': 'equipment',
                    'description': 'Industrial machinery and manufacturing equipment',
                    'max_loan_to_value': Decimal('60.00'),
                    'depreciation_rate': Decimal('10.00'),
                    'risk_level': 'high',
                    'liquidity_score': 3,
                    'requires_insurance': True,
                    'requires_professional_valuation': True,
                },
                {
                    'name': 'Office Equipment',
                    'category': 'equipment',
                    'description': 'Computers, printers, and office technology',
                    'max_loan_to_value': Decimal('50.00'),
                    'depreciation_rate': Decimal('20.00'),
                    'risk_level': 'high',
                    'liquidity_score': 4,
                    'requires_insurance': False,
                    'requires_professional_valuation': False,
                },
                {
                    'name': 'Government Bonds',
                    'category': 'securities',
                    'description': 'Government-issued bonds and securities',
                    'max_loan_to_value': Decimal('90.00'),
                    'depreciation_rate': Decimal('0.50'),
                    'risk_level': 'low',
                    'liquidity_score': 9,
                    'requires_insurance': False,
                    'requires_professional_valuation': False,
                },
                {
                    'name': 'Corporate Stocks',
                    'category': 'securities',
                    'description': 'Publicly traded corporate stocks',
                    'max_loan_to_value': Decimal('70.00'),
                    'depreciation_rate': Decimal('5.00'),
                    'risk_level': 'high',
                    'liquidity_score': 10,
                    'requires_insurance': False,
                    'requires_professional_valuation': False,
                },
                {
                    'name': 'Retail Inventory',
                    'category': 'inventory',
                    'description': 'Finished goods ready for sale',
                    'max_loan_to_value': Decimal('40.00'),
                    'depreciation_rate': Decimal('25.00'),
                    'risk_level': 'very_high',
                    'liquidity_score': 6,
                    'requires_insurance': True,
                    'requires_professional_valuation': True,
                },
                {
                    'name': 'Fixed Deposit',
                    'category': 'cash_deposit',
                    'description': 'Bank fixed deposits and certificates of deposit',
                    'max_loan_to_value': Decimal('95.00'),
                    'depreciation_rate': Decimal('0.00'),
                    'risk_level': 'low',
                    'liquidity_score': 8,
                    'requires_insurance': False,
                    'requires_professional_valuation': False,
                },
            ]
            
            created_types = []
            for type_data in collateral_types:
                collateral_type, created = CollateralType.objects.get_or_create(
                    name=type_data['name'],
                    defaults=type_data
                )
                created_types.append(collateral_type)
                if created:
                    self.stdout.write(f'✓ Created collateral type: {collateral_type.name}')
                else:
                    self.stdout.write(f'• Already exists: {collateral_type.name}')
            
            # Create sample collateral items if we have loan applications
            self.stdout.write('\nCreating sample collateral items...')
            
            loan_applications = LoanApplication.objects.select_related('customer')[:5]
            if not loan_applications:
                self.stdout.write('⚠ No loan applications found. Create some loan applications first to add sample collateral.')
                return
            
            sample_collaterals = [
                {
                    'loan_application': loan_applications[0] if len(loan_applications) > 0 else None,
                    'collateral_type': created_types[0],  # Residential Property
                    'title': '3-Bedroom Family Home',
                    'description': 'Modern 3-bedroom, 2-bathroom house in residential neighborhood with garage and garden',
                    'location': '123 Elm Street, Springfield, IL 62701',
                    'condition': 'good',
                    'owner_name': 'John Smith',
                    'ownership_document': 'Title Deed #TD-2023-456',
                    'registration_number': 'PROP-456-2023',
                    'declared_value': Decimal('185000.00'),
                    'market_value': Decimal('180000.00'),
                    'status': 'verified',
                },
                {
                    'loan_application': loan_applications[1] if len(loan_applications) > 1 else loan_applications[0],
                    'collateral_type': created_types[2],  # Passenger Vehicle
                    'title': '2022 Toyota Camry',
                    'description': 'Low mileage sedan in excellent condition with all maintenance records',
                    'location': 'Springfield, IL',
                    'condition': 'excellent',
                    'owner_name': 'Sarah Johnson',
                    'ownership_document': 'Vehicle Title #VT-2022-789',
                    'registration_number': 'ABC-1234',
                    'declared_value': Decimal('28000.00'),
                    'market_value': Decimal('26500.00'),
                    'status': 'approved',
                },
                {
                    'loan_application': loan_applications[2] if len(loan_applications) > 2 else loan_applications[0],
                    'collateral_type': created_types[1],  # Commercial Property
                    'title': 'Downtown Office Building',
                    'description': '4-story office building with retail space on ground floor, fully leased',
                    'location': '456 Main Street, Downtown Springfield',
                    'condition': 'very_good',
                    'owner_name': 'Springfield Holdings LLC',
                    'ownership_document': 'Commercial Title #CT-2021-123',
                    'registration_number': 'COMM-123-2021',
                    'declared_value': Decimal('750000.00'),
                    'market_value': Decimal('720000.00'),
                    'status': 'valued',
                },
                {
                    'loan_application': loan_applications[3] if len(loan_applications) > 3 else loan_applications[0],
                    'collateral_type': created_types[4],  # Manufacturing Equipment
                    'title': 'Industrial CNC Machine',
                    'description': 'High-precision CNC machining center with computerized controls',
                    'location': 'Factory Floor, Industrial District',
                    'condition': 'good',
                    'owner_name': 'ManuTech Industries',
                    'ownership_document': 'Equipment Invoice #EQ-2020-555',
                    'registration_number': 'CNC-555-2020',
                    'declared_value': Decimal('120000.00'),
                    'market_value': Decimal('95000.00'),
                    'status': 'pending',
                },
                {
                    'loan_application': loan_applications[4] if len(loan_applications) > 4 else loan_applications[0],
                    'collateral_type': created_types[6],  # Government Bonds
                    'title': 'US Treasury Bonds Portfolio',
                    'description': 'Diversified portfolio of 10-year US Treasury bonds',
                    'location': 'Investment Account #INV-789456',
                    'condition': 'excellent',
                    'owner_name': 'Investment Trust Fund',
                    'ownership_document': 'Bond Certificates #BC-2023-999',
                    'registration_number': 'BONDS-999-2023',
                    'declared_value': Decimal('50000.00'),
                    'market_value': Decimal('48500.00'),
                    'status': 'approved',
                },
            ]
            
            for collateral_data in sample_collaterals:
                if collateral_data['loan_application']:  # Only create if we have a loan application
                    collateral, created = Collateral.objects.get_or_create(
                        title=collateral_data['title'],
                        loan_application=collateral_data['loan_application'],
                        defaults=collateral_data
                    )
                    if created:
                        self.stdout.write(f'✓ Created collateral: {collateral.title} ({collateral.collateral_id})')
                    else:
                        self.stdout.write(f'• Already exists: {collateral.title} ({collateral.collateral_id})')
            
            self.stdout.write(f'\n🎉 Sample data creation completed!')
            self.stdout.write(f'📊 Created {len(created_types)} collateral types')
            self.stdout.write(f'🏠 Created sample collateral items for {len(loan_applications)} loan applications')
            self.stdout.write(f'\n🌐 Visit http://localhost:8000/loans/collateral/ to see the dashboard')
