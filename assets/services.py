"""
Enterprise-grade Fixed Asset Services
Implements depreciation calculations, asset lifecycle management, and reporting
"""

from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone
import calendar


class DepreciationCalculator:
    """
    Enterprise-grade depreciation calculation engine
    Supports all 6 depreciation methods from template with high precision
    """
    
    def __init__(self):
        self.precision = Decimal('0.01')  # 2 decimal places
    
    def calculate_annual_depreciation(self, asset):
        """
        Calculate annual depreciation based on asset configuration
        Returns: Decimal - annual depreciation amount
        """
        if asset.depreciation_method == 'none':
            return Decimal('0.00')
        
        purchase_price = Decimal(str(asset.purchase_price))
        residual_value = Decimal(str(asset.residual_value))
        depreciable_amount = purchase_price - residual_value
        
        if asset.depreciation_method == 'full_purchase':
            return depreciable_amount
        
        if asset.depreciation_basis == 'rate' and asset.depreciation_rate:
            rate = Decimal(str(asset.depreciation_rate)) / Decimal('100')
            return (purchase_price * rate).quantize(self.precision, ROUND_HALF_UP)
        
        if asset.depreciation_basis == 'effective_life' and asset.effective_life:
            life_years = Decimal(str(asset.effective_life))
            
            if asset.depreciation_method == 'straight_line':
                return (depreciable_amount / life_years).quantize(self.precision, ROUND_HALF_UP)
            
            elif asset.depreciation_method == 'declining_balance':
                rate = Decimal('1.0') / life_years
                return (purchase_price * rate).quantize(self.precision, ROUND_HALF_UP)
            
            elif asset.depreciation_method == 'declining_balance_150':
                rate = Decimal('1.5') / life_years
                return (purchase_price * rate).quantize(self.precision, ROUND_HALF_UP)
            
            elif asset.depreciation_method == 'declining_balance_200':
                rate = Decimal('2.0') / life_years
                return (purchase_price * rate).quantize(self.precision, ROUND_HALF_UP)
        
        return Decimal('0.00')
    
    def calculate_monthly_depreciation(self, asset, month_date=None):
        """
        Calculate monthly depreciation with averaging method consideration
        Returns: Decimal - monthly depreciation amount
        """
        annual_depreciation = self.calculate_annual_depreciation(asset)
        
        if annual_depreciation == Decimal('0.00'):
            return Decimal('0.00')
        
        if asset.averaging_method == 'full_month':
            return (annual_depreciation / Decimal('12')).quantize(self.precision, ROUND_HALF_UP)
        
        elif asset.averaging_method == 'actual_days':
            if month_date:
                days_in_month = calendar.monthrange(month_date.year, month_date.month)[1]
                daily_depreciation = annual_depreciation / Decimal('365')
                return (daily_depreciation * Decimal(str(days_in_month))).quantize(self.precision, ROUND_HALF_UP)
            else:
                # Default to average month (30.42 days)
                return (annual_depreciation / Decimal('12')).quantize(self.precision, ROUND_HALF_UP)
        
        return (annual_depreciation / Decimal('12')).quantize(self.precision, ROUND_HALF_UP)
    
    def generate_depreciation_schedule(self, asset, years=None):
        """
        Generate complete depreciation schedule for asset
        Returns: List of dictionaries with year-by-year breakdown
        """
        if not years:
            years = asset.effective_life or 5
        
        years = min(years, 10)  # Limit to 10 years for performance
        
        schedule = []
        beginning_value = Decimal(str(asset.purchase_price))
        residual_value = Decimal(str(asset.residual_value))
        total_accumulated = Decimal('0.00')
        
        start_date = asset.depreciation_start_date or asset.purchase_date
        
        for year in range(1, years + 1):
            period_start = start_date.replace(year=start_date.year + year - 1)
            period_end = start_date.replace(year=start_date.year + year) - relativedelta(days=1)
            
            # Calculate depreciation for this year
            if asset.depreciation_method in ['declining_balance', 'declining_balance_150', 'declining_balance_200']:
                yearly_depreciation = self._calculate_declining_balance_for_year(
                    asset, beginning_value, year
                )
            else:
                yearly_depreciation = self.calculate_annual_depreciation(asset)
            
            # Don't depreciate below residual value
            if beginning_value - yearly_depreciation < residual_value:
                yearly_depreciation = max(Decimal('0.00'), beginning_value - residual_value)
            
            total_accumulated += yearly_depreciation
            ending_value = beginning_value - yearly_depreciation
            
            schedule.append({
                'year': year,
                'period_start_date': period_start,
                'period_end_date': period_end,
                'beginning_book_value': beginning_value,
                'depreciation_amount': yearly_depreciation,
                'accumulated_depreciation': total_accumulated,
                'ending_book_value': ending_value,
            })
            
            beginning_value = ending_value
            
            # Stop if we've reached residual value
            if ending_value <= residual_value:
                break
        
        return schedule
    
    def _calculate_declining_balance_for_year(self, asset, beginning_value, year):
        """Calculate declining balance depreciation for specific year"""
        if not asset.effective_life:
            return Decimal('0.00')
        
        life_years = Decimal(str(asset.effective_life))
        
        if asset.depreciation_method == 'declining_balance':
            rate = Decimal('1.0') / life_years
        elif asset.depreciation_method == 'declining_balance_150':
            rate = Decimal('1.5') / life_years
        elif asset.depreciation_method == 'declining_balance_200':
            rate = Decimal('2.0') / life_years
        else:
            rate = Decimal('1.0') / life_years
        
        return (beginning_value * rate).quantize(self.precision, ROUND_HALF_UP)
    
    def get_current_book_value(self, asset, as_of_date=None):
        """
        Calculate current book value of asset
        Returns: Decimal - current book value
        """
        if not as_of_date:
            as_of_date = timezone.now().date()
        
        # If asset hasn't started depreciating yet
        start_date = asset.depreciation_start_date or asset.purchase_date
        if as_of_date < start_date:
            return Decimal(str(asset.purchase_price))
        
        # Calculate accumulated depreciation to date
        accumulated = self.get_accumulated_depreciation(asset, as_of_date)
        current_value = Decimal(str(asset.purchase_price)) - accumulated
        
        # Don't go below residual value
        residual = Decimal(str(asset.residual_value))
        return max(current_value, residual)
    
    def get_accumulated_depreciation(self, asset, as_of_date=None):
        """
        Calculate accumulated depreciation to date
        Returns: Decimal - total accumulated depreciation
        """
        if not as_of_date:
            as_of_date = timezone.now().date()
        
        start_date = asset.depreciation_start_date or asset.purchase_date
        if as_of_date < start_date:
            return Decimal('0.00')
        
        if asset.depreciation_method == 'none':
            return Decimal('0.00')
        
        # Calculate months between start date and as_of_date
        months_elapsed = self._calculate_months_between(start_date, as_of_date)
        
        if asset.depreciation_method == 'full_purchase':
            return Decimal(str(asset.purchase_price)) - Decimal(str(asset.residual_value))
        
        # For other methods, calculate based on monthly depreciation
        monthly_depreciation = self.calculate_monthly_depreciation(asset)
        total_accumulated = monthly_depreciation * Decimal(str(months_elapsed))
        
        # Don't exceed depreciable amount
        max_depreciation = Decimal(str(asset.purchase_price)) - Decimal(str(asset.residual_value))
        return min(total_accumulated, max_depreciation).quantize(self.precision, ROUND_HALF_UP)
    
    def _calculate_months_between(self, start_date, end_date):
        """Calculate number of months between two dates"""
        if end_date < start_date:
            return 0
        
        months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        
        # Add partial month if end day is after start day
        if end_date.day >= start_date.day:
            months += 1
        
        return months


class AssetLifecycleManager:
    """
    Manages complete asset lifecycle from creation to disposal
    Handles business logic, validations, and integrations
    """
    
    def __init__(self):
        self.calculator = DepreciationCalculator()
    
    def create_asset(self, asset_data, created_by):
        """
        Create new asset with validation and automatic number generation
        Returns: FixedAsset instance
        """
        from .models import FixedAsset, AssetTransaction
        
        with transaction.atomic():
            # Create the asset
            asset = FixedAsset.objects.create(
                created_by=created_by,
                **asset_data
            )
            
            # Create acquisition transaction
            AssetTransaction.objects.create(
                asset=asset,
                transaction_type='acquisition',
                transaction_date=asset.purchase_date,
                amount=asset.purchase_price,
                description=f"Initial acquisition of {asset.name}",
                created_by=created_by
            )
            
            return asset
    
    def register_asset(self, asset, registered_by):
        """
        Move asset from draft to registered status
        Creates depreciation schedule and initial journal entries
        """
        from .models import AssetTransaction, DepreciationSchedule
        
        if asset.status != 'draft':
            raise ValueError("Only draft assets can be registered")
        
        with transaction.atomic():
            # Update status
            asset.status = 'registered'
            asset.save()
            
            # Generate depreciation schedule
            if asset.depreciation_method != 'none':
                schedule_data = self.calculator.generate_depreciation_schedule(asset)
                
                # Create schedule records
                for period in schedule_data:
                    DepreciationSchedule.objects.create(
                        asset=asset,
                        year=period['year'],
                        period_start_date=period['period_start_date'],
                        period_end_date=period['period_end_date'],
                        beginning_book_value=period['beginning_book_value'],
                        depreciation_amount=period['depreciation_amount'],
                        accumulated_depreciation=period['accumulated_depreciation'],
                        ending_book_value=period['ending_book_value'],
                        is_tax_schedule=False
                    )
                    
                    # Create tax schedule if separate tax depreciation is enabled
                    if asset.separate_tax_depreciation:
                        DepreciationSchedule.objects.create(
                            asset=asset,
                            year=period['year'],
                            period_start_date=period['period_start_date'],
                            period_end_date=period['period_end_date'],
                            beginning_book_value=period['beginning_book_value'],
                            depreciation_amount=period['depreciation_amount'],  # TODO: Calculate tax depreciation
                            accumulated_depreciation=period['accumulated_depreciation'],
                            ending_book_value=period['ending_book_value'],
                            is_tax_schedule=True
                        )
            
            # Create registration transaction
            AssetTransaction.objects.create(
                asset=asset,
                transaction_type='acquisition',
                transaction_date=timezone.now().date(),
                amount=Decimal('0.00'),
                description=f"Asset registered by {registered_by.get_full_name() or registered_by.username}",
                created_by=registered_by
            )
            
            # TODO: Create journal entries for asset acquisition
            # self.create_acquisition_journal_entry(asset)
    
    def dispose_asset(self, asset, disposal_data, disposed_by):
        """
        Handle asset disposal with gain/loss calculation
        Creates disposal transaction and journal entries
        """
        from .models import AssetDisposal, AssetTransaction
        
        if asset.status == 'disposed':
            raise ValueError("Asset is already disposed")
        
        with transaction.atomic():
            # Calculate current book value
            book_value = self.calculator.get_current_book_value(
                asset, disposal_data['disposal_date']
            )
            
            # Create disposal record
            disposal = AssetDisposal.objects.create(
                asset=asset,
                disposal_date=disposal_data['disposal_date'],
                disposal_method=disposal_data['disposal_method'],
                disposal_value=disposal_data['disposal_value'],
                book_value_at_disposal=book_value,
                buyer_details=disposal_data.get('buyer_details', ''),
                disposal_costs=disposal_data.get('disposal_costs', Decimal('0.00')),
                created_by=disposed_by
            )
            
            # Update asset status
            asset.status = 'disposed'
            asset.save()
            
            # Create disposal transaction
            AssetTransaction.objects.create(
                asset=asset,
                transaction_type='disposal',
                transaction_date=disposal_data['disposal_date'],
                amount=disposal_data['disposal_value'],
                description=f"Asset disposal via {disposal_data['disposal_method']}",
                created_by=disposed_by
            )
            
            # TODO: Create disposal journal entries
            # self.create_disposal_journal_entry(asset, disposal)
            
            return disposal
    
    def transfer_asset(self, asset, new_location, transferred_by, notes=""):
        """
        Transfer asset to new location/department
        """
        from .models import AssetTransaction
        
        old_location = asset.location
        
        with transaction.atomic():
            asset.location = new_location
            asset.save()
            
            # Create transfer transaction
            AssetTransaction.objects.create(
                asset=asset,
                transaction_type='revaluation',  # Using revaluation type for transfers
                transaction_date=timezone.now().date(),
                amount=Decimal('0.00'),
                description=f"Transferred from '{old_location}' to '{new_location}'. {notes}",
                created_by=transferred_by
            )


class AssetReportingService:
    """
    Generate comprehensive asset reports and analytics
    """
    
    def __init__(self):
        self.calculator = DepreciationCalculator()
    
    def asset_register_report(self, company, as_of_date=None):
        """
        Generate complete asset register report
        Returns: List of dictionaries with asset summary data
        """
        from .models import FixedAsset
        
        if not as_of_date:
            as_of_date = timezone.now().date()
        
        assets = FixedAsset.objects.filter(
            company=company,
            purchase_date__lte=as_of_date
        ).exclude(
            status='disposed'
        ).select_related('asset_type').order_by('number')
        
        report_data = []
        total_cost = Decimal('0.00')
        total_accumulated = Decimal('0.00')
        total_book_value = Decimal('0.00')
        
        for asset in assets:
            accumulated_depreciation = self.calculator.get_accumulated_depreciation(asset, as_of_date)
            book_value = self.calculator.get_current_book_value(asset, as_of_date)
            
            report_data.append({
                'asset_number': asset.number,
                'asset_name': asset.name,
                'asset_type': asset.asset_type.name,
                'location': asset.location,
                'purchase_date': asset.purchase_date,
                'purchase_price': asset.purchase_price,
                'accumulated_depreciation': accumulated_depreciation,
                'book_value': book_value,
                'status': asset.get_status_display(),
                'depreciation_method': asset.get_depreciation_method_display(),
            })
            
            total_cost += asset.purchase_price
            total_accumulated += accumulated_depreciation
            total_book_value += book_value
        
        return {
            'assets': report_data,
            'summary': {
                'total_cost': total_cost,
                'total_accumulated_depreciation': total_accumulated,
                'total_book_value': total_book_value,
                'asset_count': len(report_data),
                'as_of_date': as_of_date,
            }
        }
    
    def depreciation_report(self, company, period_start, period_end):
        """
        Generate depreciation report for specified period
        """
        from .models import FixedAsset
        
        assets = FixedAsset.objects.filter(
            company=company,
            status='registered',
            depreciation_start_date__lte=period_end
        ).select_related('asset_type')
        
        report_data = []
        total_depreciation = Decimal('0.00')
        
        for asset in assets:
            if asset.depreciation_method == 'none':
                continue
            
            # Calculate depreciation for the period
            period_depreciation = self._calculate_period_depreciation(
                asset, period_start, period_end
            )
            
            if period_depreciation > Decimal('0.00'):
                report_data.append({
                    'asset_number': asset.number,
                    'asset_name': asset.name,
                    'asset_type': asset.asset_type.name,
                    'depreciation_method': asset.get_depreciation_method_display(),
                    'period_depreciation': period_depreciation,
                    'monthly_depreciation': self.calculator.calculate_monthly_depreciation(asset),
                })
                
                total_depreciation += period_depreciation
        
        return {
            'depreciation_entries': report_data,
            'total_period_depreciation': total_depreciation,
            'period_start': period_start,
            'period_end': period_end,
        }
    
    def _calculate_period_depreciation(self, asset, period_start, period_end):
        """Calculate depreciation for specific period"""
        start_date = max(asset.depreciation_start_date or asset.purchase_date, period_start)
        end_date = min(period_end, timezone.now().date())
        
        if start_date > end_date:
            return Decimal('0.00')
        
        months_in_period = self.calculator._calculate_months_between(start_date, end_date)
        monthly_depreciation = self.calculator.calculate_monthly_depreciation(asset)
        
        return (monthly_depreciation * Decimal(str(months_in_period))).quantize(
            Decimal('0.01'), ROUND_HALF_UP
        )
    
    def upcoming_disposals_report(self, company, months_ahead=12):
        """
        Generate report of assets due for disposal
        """
        from .models import FixedAsset
        
        cutoff_date = timezone.now().date() + relativedelta(months=months_ahead)
        
        assets = FixedAsset.objects.filter(
            company=company,
            status='registered',
            expected_disposal_date__lte=cutoff_date,
            expected_disposal_date__gte=timezone.now().date()
        ).select_related('asset_type').order_by('expected_disposal_date')
        
        report_data = []
        for asset in assets:
            book_value = self.calculator.get_current_book_value(asset)
            estimated_gain_loss = asset.estimated_disposal_value - book_value
            
            report_data.append({
                'asset_number': asset.number,
                'asset_name': asset.name,
                'asset_type': asset.asset_type.name,
                'expected_disposal_date': asset.expected_disposal_date,
                'disposal_method': asset.get_disposal_method_display() if asset.disposal_method else 'Not specified',
                'current_book_value': book_value,
                'estimated_disposal_value': asset.estimated_disposal_value,
                'estimated_gain_loss': estimated_gain_loss,
            })
        
        return report_data
