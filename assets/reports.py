"""
Fixed Asset Accounting Reports Services
Comprehensive reporting for balance sheet, trial balance, and tax reporting
"""

from decimal import Decimal
from datetime import date
from django.db.models import Sum
from django.utils import timezone

from .models import FixedAsset, AssetType, AssetDisposal
from .services import DepreciationCalculator


class AssetAccountingReports:
    """
    Main service class for generating accounting-focused asset reports
    """
    
    def __init__(self, company=None, as_of_date=None):
        self.company = company
        self.as_of_date = as_of_date or timezone.now().date()
        self.calculator = DepreciationCalculator()
    
    # ===== BALANCE SHEET REPORTING =====
    
    def get_balance_sheet_assets(self):
        """
        Generate balance sheet asset values by category
        Returns: Dict with cost, accumulated depreciation, and net book value
        """
        queryset = self._get_base_queryset()
        
        # Get assets by category with totals
        categories = AssetType.objects.filter(is_active=True)
        balance_sheet_data = []
        
        total_cost = Decimal('0.00')
        total_accumulated_dep = Decimal('0.00')
        
        for category in categories:
            category_assets = queryset.filter(asset_type=category)
            
            if category_assets.exists():
                cost = category_assets.aggregate(
                    total=Sum('purchase_price')
                )['total'] or Decimal('0.00')
                
                # Calculate accumulated depreciation using the property method
                accumulated_dep = Decimal('0.00')
                for asset in category_assets:
                    accumulated_dep += asset.total_accumulated_depreciation
                
                net_book_value = cost - accumulated_dep
                
                balance_sheet_data.append({
                    'category': category,
                    'cost': cost,
                    'accumulated_depreciation': accumulated_dep,
                    'net_book_value': net_book_value,
                    'gl_asset_account': self._get_asset_gl_account(category),
                    'gl_depreciation_account': self._get_accumulated_dep_gl_account(category)
                })
                
                total_cost += cost
                total_accumulated_dep += accumulated_dep
        
        return {
            'categories': balance_sheet_data,
            'totals': {
                'total_cost': total_cost,
                'total_accumulated_depreciation': total_accumulated_dep,
                'net_book_value': total_cost - total_accumulated_dep
            },
            'as_of_date': self.as_of_date
        }
    
    # ===== TRIAL BALANCE REPORTING =====
    
    def get_trial_balance_assets(self):
        """
        Generate trial balance entries for fixed assets
        Returns: List of GL account balances for trial balance
        """
        balance_sheet_data = self.get_balance_sheet_assets()
        trial_balance = []
        
        # Asset accounts (Debit balances)
        for category_data in balance_sheet_data['categories']:
            if category_data['cost'] > 0:
                trial_balance.append({
                    'account_code': category_data['gl_asset_account'],
                    'account_name': f"{category_data['category'].name} - Cost",
                    'debit': category_data['cost'],
                    'credit': Decimal('0.00'),
                    'balance_type': 'asset'
                })
        
        # Accumulated depreciation accounts (Credit balances)
        for category_data in balance_sheet_data['categories']:
            if category_data['accumulated_depreciation'] > 0:
                trial_balance.append({
                    'account_code': category_data['gl_depreciation_account'],
                    'account_name': f"Accumulated Depreciation - {category_data['category'].name}",
                    'debit': Decimal('0.00'),
                    'credit': category_data['accumulated_depreciation'],
                    'balance_type': 'contra_asset'
                })
        
        # Calculate totals
        total_debits = sum(item['debit'] for item in trial_balance)
        total_credits = sum(item['credit'] for item in trial_balance)
        
        return {
            'accounts': trial_balance,
            'totals': {
                'total_debits': total_debits,
                'total_credits': total_credits,
                'net_assets': total_debits - total_credits
            },
            'as_of_date': self.as_of_date
        }
    
    # ===== TAX DEPRECIATION REPORTING =====
    
    def get_tax_depreciation_schedule(self, tax_year=None):
        """
        Generate annual tax depreciation schedule
        Returns: Asset-by-asset depreciation for tax returns
        """
        if not tax_year:
            tax_year = self.as_of_date.year
        
        queryset = self._get_base_queryset()
        active_assets = queryset.filter(status='active')
        
        schedule = []
        total_book_depreciation = Decimal('0.00')
        total_tax_depreciation = Decimal('0.00')
        
        for asset in active_assets:
            # Calculate book depreciation for the year
            book_depreciation = self._calculate_annual_book_depreciation(asset, tax_year)
            
            # Calculate tax depreciation (could be different method)
            tax_depreciation = self._calculate_annual_tax_depreciation(asset, tax_year)
            
            if book_depreciation > 0 or tax_depreciation > 0:
                schedule.append({
                    'asset': asset,
                    'date_acquired': asset.purchase_date,
                    'cost': asset.purchase_price,
                    'depreciation_method': asset.get_depreciation_method_display(),
                    'book_depreciation': book_depreciation,
                    'tax_depreciation': tax_depreciation,
                    'difference': tax_depreciation - book_depreciation,
                    'accumulated_book': asset.total_accumulated_depreciation,
                    'remaining_book_value': asset.purchase_price - asset.total_accumulated_depreciation
                })
                
                total_book_depreciation += book_depreciation
                total_tax_depreciation += tax_depreciation
        
        return {
            'year': tax_year,
            'schedule': schedule,
            'totals': {
                'total_book_depreciation': total_book_depreciation,
                'total_tax_depreciation': total_tax_depreciation,
                'timing_difference': total_tax_depreciation - total_book_depreciation
            }
        }
    
    # ===== ASSET MOVEMENTS REPORTING =====
    
    def get_asset_movements_report(self, start_date=None, end_date=None):
        """
        Generate asset additions, disposals, and transfers for period
        Returns: All asset transactions for the period
        """
        if not start_date:
            start_date = date(self.as_of_date.year, 1, 1)  # Start of year
        if not end_date:
            end_date = self.as_of_date
        
        # Get additions (new assets purchased)
        additions = FixedAsset.objects.filter(
            company=self.company,
            purchase_date__range=[start_date, end_date]
        ).order_by('purchase_date')
        
        # Get disposals
        disposals = AssetDisposal.objects.filter(
            asset__company=self.company,
            disposal_date__range=[start_date, end_date]
        ).select_related('asset').order_by('disposal_date')
        
        # Calculate totals
        total_additions_cost = additions.aggregate(
            total=Sum('purchase_price')
        )['total'] or Decimal('0.00')
        
        total_disposal_proceeds = disposals.aggregate(
            total=Sum('disposal_value')
        )['total'] or Decimal('0.00')
        
        total_disposal_book_value = sum(
            disposal.asset.purchase_price - disposal.asset.accumulated_depreciation
            for disposal in disposals
        )
        
        gain_loss_on_disposal = total_disposal_proceeds - total_disposal_book_value
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'additions': {
                'assets': additions,
                'total_cost': total_additions_cost,
                'count': additions.count()
            },
            'disposals': {
                'transactions': disposals,
                'total_proceeds': total_disposal_proceeds,
                'total_book_value': total_disposal_book_value,
                'gain_loss': gain_loss_on_disposal,
                'count': disposals.count()
            }
        }
    
    # ===== DEPRECIATION EXPENSE REPORTING =====
    
    def get_depreciation_expense_summary(self, year=None):
        """
        Generate depreciation expense summary for P&L
        Returns: Depreciation expense by category and total
        """
        if not year:
            year = self.as_of_date.year
        
        queryset = self._get_base_queryset()
        categories = AssetType.objects.filter(is_active=True)
        
        expense_summary = []
        total_book_expense = Decimal('0.00')
        total_tax_expense = Decimal('0.00')
        
        for category in categories:
            category_assets = queryset.filter(asset_type=category, status='active')
            
            if category_assets.exists():
                category_book_expense = Decimal('0.00')
                category_tax_expense = Decimal('0.00')
                
                for asset in category_assets:
                    book_dep = self._calculate_annual_book_depreciation(asset, year)
                    tax_dep = self._calculate_annual_tax_depreciation(asset, year)
                    
                    category_book_expense += book_dep
                    category_tax_expense += tax_dep
                
                if category_book_expense > 0 or category_tax_expense > 0:
                    expense_summary.append({
                        'category': category,
                        'book_depreciation': category_book_expense,
                        'tax_depreciation': category_tax_expense,
                        'timing_difference': category_tax_expense - category_book_expense,
                        'gl_expense_account': self._get_depreciation_expense_gl_account(category)
                    })
                    
                    total_book_expense += category_book_expense
                    total_tax_expense += category_tax_expense
        
        return {
            'year': year,
            'categories': expense_summary,
            'totals': {
                'total_book_expense': total_book_expense,
                'total_tax_expense': total_tax_expense,
                'total_timing_difference': total_tax_expense - total_book_expense
            }
        }
    
    # ===== HELPER METHODS =====
    
    def _get_base_queryset(self):
        """Get base queryset filtered by company and date"""
        queryset = FixedAsset.objects.select_related('asset_type')
        
        if self.company:
            queryset = queryset.filter(company=self.company)
        
        # Filter by purchase date (assets must exist as of report date)
        queryset = queryset.filter(purchase_date__lte=self.as_of_date)
        
        return queryset
    
    def _calculate_annual_book_depreciation(self, asset, year):
        """Calculate annual book depreciation for specific year"""
        if asset.depreciation_method == 'none':
            return Decimal('0.00')
        
        # Use the calculator service for consistency
        monthly_depreciation = self.calculator.calculate_monthly_depreciation(asset)
        
        # Determine how many months of depreciation in the year
        asset_start_year = max(asset.depreciation_start_date.year, year)
        
        if asset_start_year > year:
            return Decimal('0.00')  # Asset not yet depreciating
        
        if asset_start_year == year:
            # Partial year depreciation
            months_in_year = 13 - asset.depreciation_start_date.month
        else:
            # Full year
            months_in_year = 12
        
        return monthly_depreciation * months_in_year
    
    def _calculate_annual_tax_depreciation(self, asset, year):
        """Calculate annual tax depreciation (may differ from book)"""
        if asset.separate_tax_depreciation and asset.tax_depreciation_method:
            # Use tax method if separate tax depreciation is enabled
            # For now, use the same calculation - can be enhanced later
            return self._calculate_annual_book_depreciation(asset, year)
        else:
            # Use book method for tax
            return self._calculate_annual_book_depreciation(asset, year)
    
    def _get_asset_gl_account(self, asset_type):
        """Get GL account code for asset type"""
        # This should be configurable in the future
        gl_mapping = {
            'COMP': '1410',      # Computer Equipment
            'OFFICE': '1420',    # Office Furniture
            'MACH': '1430',      # Machinery
            'VEH': '1440',       # Vehicles
            'BLDG': '1450',      # Buildings
        }
        return gl_mapping.get(asset_type.code, '1400')  # Default fixed asset account
    
    def _get_accumulated_dep_gl_account(self, asset_type):
        """Get GL account code for accumulated depreciation"""
        gl_mapping = {
            'COMP': '1510',      # Accumulated Dep - Computer
            'OFFICE': '1520',    # Accumulated Dep - Furniture
            'MACH': '1530',      # Accumulated Dep - Machinery
            'VEH': '1540',       # Accumulated Dep - Vehicles
            'BLDG': '1550',      # Accumulated Dep - Buildings
        }
        return gl_mapping.get(asset_type.code, '1500')  # Default accumulated dep account
    
    def _get_depreciation_expense_gl_account(self, asset_type):
        """Get GL account code for depreciation expense"""
        # Most companies use one depreciation expense account
        return '6300'  # Depreciation Expense


class BalanceSheetIntegration:
    """
    Service for integrating fixed assets with balance sheet preparation
    """
    
    @staticmethod
    def get_fixed_assets_for_balance_sheet(company, as_of_date):
        """
        Get fixed assets summary for balance sheet line items
        Returns formatted data for balance sheet integration
        """
        reports = AssetAccountingReports(company=company, as_of_date=as_of_date)
        balance_data = reports.get_balance_sheet_assets()
        
        return {
            'gross_fixed_assets': balance_data['totals']['total_cost'],
            'accumulated_depreciation': balance_data['totals']['total_accumulated_depreciation'],
            'net_fixed_assets': balance_data['totals']['net_book_value'],
            'detail_by_category': balance_data['categories']
        }


class TrialBalanceIntegration:
    """
    Service for integrating fixed assets with trial balance
    """
    
    @staticmethod
    def get_asset_trial_balance_entries(company, as_of_date):
        """
        Get trial balance entries for fixed assets
        Returns GL account balances for trial balance
        """
        reports = AssetAccountingReports(company=company, as_of_date=as_of_date)
        trial_balance_data = reports.get_trial_balance_assets()
        
        # Format for trial balance integration
        entries = []
        for account in trial_balance_data['accounts']:
            entries.append({
                'account_code': account['account_code'],
                'account_name': account['account_name'],
                'debit_balance': account['debit'],
                'credit_balance': account['credit'],
                'account_type': account['balance_type']
            })
        
        return {
            'entries': entries,
            'total_asset_debits': trial_balance_data['totals']['total_debits'],
            'total_contra_credits': trial_balance_data['totals']['total_credits']
        }
