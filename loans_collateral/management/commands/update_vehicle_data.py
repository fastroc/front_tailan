from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from loans_collateral.models import Collateral, CollateralType
from loans_core.models import LoanApplication


class Command(BaseCommand):
    help = 'Update existing vehicle collateral with detailed vehicle information'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Updating vehicle collateral with detailed information...')
            
            # Find existing vehicle collateral
            vehicle_collaterals = Collateral.objects.filter(
                collateral_type__category='vehicle'
            ).select_related('collateral_type')
            
            if not vehicle_collaterals:
                self.stdout.write('No existing vehicle collateral found. Creating new sample...')
                
                # Get vehicle collateral types
                passenger_vehicle = CollateralType.objects.filter(
                    category='vehicle', 
                    name__icontains='Passenger'
                ).first()
                
                commercial_vehicle = CollateralType.objects.filter(
                    category='vehicle', 
                    name__icontains='Commercial'
                ).first()
                
                if not passenger_vehicle or not commercial_vehicle:
                    self.stdout.write('Vehicle collateral types not found. Run populate_collateral_data first.')
                    return
                
                # Get some loan applications
                loan_applications = list(LoanApplication.objects.all()[:3])
                if not loan_applications:
                    self.stdout.write('No loan applications found. Create some loan applications first.')
                    return
                
                # Create new vehicle collateral with details
                sample_vehicles = [
                    {
                        'loan_application': loan_applications[0],
                        'collateral_type': passenger_vehicle,
                        'title': '2021 Honda Accord Sedan',
                        'description': 'Well-maintained mid-size sedan with low mileage and full service history',
                        'location': 'Chicago, IL',
                        'condition': 'excellent',
                        'owner_name': 'Michael Johnson',
                        'ownership_document': 'Vehicle Title #VT-2021-456',
                        'registration_number': 'IL-456-2021',
                        'declared_value': Decimal('24500.00'),
                        'market_value': Decimal('23800.00'),
                        'status': 'verified',
                        # Vehicle-specific fields
                        'vehicle_make': 'Honda',
                        'vehicle_model': 'Accord',
                        'vehicle_year': 2021,
                        'vehicle_registration_year': 2021,
                        'vehicle_license_plate': 'ABC-123',
                        'vehicle_vin': '1HGCV1F3XLA123456',
                        'vehicle_mileage': 15200,
                        'vehicle_fuel_type': 'gasoline',
                    },
                    {
                        'loan_application': loan_applications[1] if len(loan_applications) > 1 else loan_applications[0],
                        'collateral_type': commercial_vehicle,
                        'title': '2020 Ford Transit Van',
                        'description': 'Commercial cargo van used for delivery services, regular maintenance records',
                        'location': 'Springfield, IL',
                        'condition': 'good',
                        'owner_name': 'Springfield Logistics LLC',
                        'ownership_document': 'Commercial Vehicle Title #CVT-2020-789',
                        'registration_number': 'IL-COM-789',
                        'declared_value': Decimal('28000.00'),
                        'market_value': Decimal('26500.00'),
                        'status': 'approved',
                        # Vehicle-specific fields
                        'vehicle_make': 'Ford',
                        'vehicle_model': 'Transit',
                        'vehicle_year': 2020,
                        'vehicle_registration_year': 2020,
                        'vehicle_license_plate': 'COM-456',
                        'vehicle_vin': '1FTBW2CM5LKA78901',
                        'vehicle_mileage': 45600,
                        'vehicle_fuel_type': 'diesel',
                    },
                    {
                        'loan_application': loan_applications[2] if len(loan_applications) > 2 else loan_applications[0],
                        'collateral_type': passenger_vehicle,
                        'title': '2022 Tesla Model 3',
                        'description': 'Electric sedan with autopilot, premium interior, excellent condition',
                        'location': 'Naperville, IL',
                        'condition': 'excellent',
                        'owner_name': 'Sarah Chen',
                        'ownership_document': 'Vehicle Title #VT-2022-321',
                        'registration_number': 'IL-321-2022',
                        'declared_value': Decimal('42000.00'),
                        'market_value': Decimal('39500.00'),
                        'status': 'pending',
                        # Vehicle-specific fields
                        'vehicle_make': 'Tesla',
                        'vehicle_model': 'Model 3',
                        'vehicle_year': 2022,
                        'vehicle_registration_year': 2022,
                        'vehicle_license_plate': 'TESLA-3',
                        'vehicle_vin': '5YJ3E1EB8KF123456',
                        'vehicle_mileage': 8500,
                        'vehicle_fuel_type': 'electric',
                    }
                ]
                
                for vehicle_data in sample_vehicles:
                    collateral, created = Collateral.objects.get_or_create(
                        title=vehicle_data['title'],
                        defaults=vehicle_data
                    )
                    if created:
                        self.stdout.write(f'✓ Created vehicle collateral: {collateral.title} ({collateral.collateral_id})')
                    else:
                        # Update existing with vehicle details
                        for field, value in vehicle_data.items():
                            if field not in ['title']:  # Don't update the lookup field
                                setattr(collateral, field, value)
                        collateral.save()
                        self.stdout.write(f'✓ Updated vehicle collateral: {collateral.title} ({collateral.collateral_id})')
            
            else:
                # Update existing vehicle collateral with sample data
                vehicle_updates = [
                    {
                        'vehicle_make': 'Toyota',
                        'vehicle_model': 'Camry',
                        'vehicle_year': 2022,
                        'vehicle_registration_year': 2022,
                        'vehicle_license_plate': 'TOY-123',
                        'vehicle_vin': '4T1C11AK5NU123456',
                        'vehicle_mileage': 12500,
                        'vehicle_fuel_type': 'gasoline',
                    },
                    {
                        'vehicle_make': 'BMW',
                        'vehicle_model': 'X5',
                        'vehicle_year': 2021,
                        'vehicle_registration_year': 2021,
                        'vehicle_license_plate': 'BMW-X5',
                        'vehicle_vin': '5UXCR6C58L9123456',
                        'vehicle_mileage': 18200,
                        'vehicle_fuel_type': 'gasoline',
                    }
                ]
                
                for i, collateral in enumerate(vehicle_collaterals):
                    if i < len(vehicle_updates):
                        update_data = vehicle_updates[i]
                        for field, value in update_data.items():
                            setattr(collateral, field, value)
                        collateral.save()
                        self.stdout.write(f'✓ Updated {collateral.title} with vehicle details')
            
            self.stdout.write('\n🚗 Vehicle collateral update completed!')
            self.stdout.write('🌐 Visit http://localhost:8001/loans/collateral/ to see the updated dashboard')
            self.stdout.write('➕ Test the Add Collateral form with vehicle types at http://localhost:8001/loans/collateral/items/create/')
