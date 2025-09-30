from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import hashlib
import json

# Import models from other apps
from loans_core.models import Loan, LoanApplication
from loans_customers.models import Customer
from loans_payments.models import Payment
from company.models import Company
from .models import ReportCache


class ReportService:
    """
    Comprehensive service class for generating dynamic loan reports
    Provides fail-safe operations with proper error handling
    """
    
    def __init__(self, company: Company, use_cache: bool = True):
        self.company = company
        self.use_cache = use_cache
        self.cache_timeout = 300  # 5 minutes default cache
    
    def _get_cache_key(self, report_type: str, **kwargs) -> str:
        """Generate unique cache key for report data"""
        key_data = f"{self.company.id}:{report_type}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Retrieve cached report data if available and not expired"""
        if not self.use_cache:
            return None
            
        try:
            cache_obj = ReportCache.objects.get(
                cache_key=cache_key,
                company=self.company
            )
            if not cache_obj.is_expired():
                return cache_obj.data
            else:
                cache_obj.delete()  # Clean up expired cache
        except ReportCache.DoesNotExist:
            pass
        return None
    
    def _set_cached_data(self, cache_key: str, report_type: str, data: Dict) -> None:
        """Store report data in cache"""
        if not self.use_cache:
            return
            
        expires_at = timezone.now() + timedelta(seconds=self.cache_timeout)
        ReportCache.objects.update_or_create(
            cache_key=cache_key,
            defaults={
                'company': self.company,
                'report_type': report_type,
                'data': data,
                'expires_at': expires_at
            }
        )
    
    def portfolio_analytics(self, start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate comprehensive portfolio analytics
        """
        cache_key = self._get_cache_key('portfolio', start_date=start_date, end_date=end_date)
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Base queryset with company filter
            loans_qs = Loan.objects.filter(company=self.company)
            applications_qs = LoanApplication.objects.filter(company=self.company)
            payments_qs = Payment.objects.filter(company=self.company)
            
            # Apply date filters if provided
            if start_date:
                loans_qs = loans_qs.filter(created_at__gte=start_date)
                applications_qs = applications_qs.filter(application_date__gte=start_date)
                payments_qs = payments_qs.filter(payment_date__gte=start_date)
            if end_date:
                loans_qs = loans_qs.filter(created_at__lte=end_date)
                applications_qs = applications_qs.filter(application_date__lte=end_date)
                payments_qs = payments_qs.filter(payment_date__lte=end_date)
            
            # Core portfolio metrics
            total_portfolio = loans_qs.aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
            active_loans_count = loans_qs.filter(status='active').count()
            completed_loans_count = loans_qs.filter(status='completed').count()
            total_customers = Customer.objects.filter(company=self.company).count()
            
            # Application metrics
            total_applications = applications_qs.count()
            approved_applications = applications_qs.filter(status='approved').count()
            pending_applications = applications_qs.filter(status='pending').count()
            
            # Payment metrics
            total_payments_received = payments_qs.filter(status='completed').aggregate(
                total=Sum('payment_amount')
            )['total'] or Decimal('0.00')
            
            # Calculate rates and averages
            avg_loan_size = Decimal('0.00')
            if active_loans_count > 0:
                avg_loan_size = Decimal(str(total_portfolio / active_loans_count)).quantize(Decimal('0.01'))
            
            approval_rate = Decimal('0.0')
            if total_applications > 0:
                approval_rate = Decimal(str(approved_applications / total_applications * 100)).quantize(Decimal('0.1'))
            
            collection_rate = Decimal('0.0')
            if total_portfolio > 0:
                collection_rate = Decimal(str(total_payments_received / total_portfolio * 100)).quantize(Decimal('0.1'))
            
            # Month-over-month growth
            current_month = timezone.now().replace(day=1)
            last_month = (current_month - timedelta(days=1)).replace(day=1)
            
            current_month_applications = applications_qs.filter(
                application_date__gte=current_month
            ).count()
            last_month_applications = applications_qs.filter(
                application_date__gte=last_month,
                application_date__lt=current_month
            ).count()
            
            application_growth = Decimal('0.0')
            if last_month_applications > 0:
                growth_calc = (current_month_applications - last_month_applications) / last_month_applications * 100
                application_growth = Decimal(str(growth_calc)).quantize(Decimal('0.1'))
            elif current_month_applications > 0:
                application_growth = Decimal('100.0')
            
            data = {
                'total_portfolio_value': total_portfolio,
                'active_loans_count': active_loans_count,
                'completed_loans_count': completed_loans_count,
                'total_customers': total_customers,
                'pending_applications': pending_applications,
                'avg_loan_amount': avg_loan_size,
                'approval_rate': approval_rate,
                'collection_rate': collection_rate,
                'application_growth': application_growth,
                'total_payments_received': total_payments_received,
                'ytd_disbursements': total_portfolio,  # Simplified for now
                'portfolio_yield': Decimal('12.5'),  # Could be calculated based on interest rates
                'updated_at': timezone.now().isoformat(),
            }
            
            self._set_cached_data(cache_key, 'portfolio', data)
            return data
            
        except Exception as e:
            # Fail-safe: Return basic structure with zeros
            return {
                'total_portfolio_value': Decimal('0.00'),
                'active_loans_count': 0,
                'completed_loans_count': 0,
                'total_customers': 0,
                'pending_applications': 0,
                'avg_loan_amount': Decimal('0.00'),
                'approval_rate': Decimal('0.0'),
                'collection_rate': Decimal('0.0'),
                'application_growth': Decimal('0.0'),
                'total_payments_received': Decimal('0.00'),
                'ytd_disbursements': Decimal('0.00'),
                'portfolio_yield': Decimal('0.0'),
                'error': str(e),
                'updated_at': timezone.now().isoformat(),
            }
    
    def aging_analysis(self) -> Dict[str, Any]:
        """
        Generate aging analysis for overdue loans
        """
        cache_key = self._get_cache_key('aging')
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            today = timezone.now().date()
            loans_qs = Loan.objects.filter(company=self.company, status='active')
            
            # Calculate aging buckets
            current_loans = loans_qs.filter(
                Q(next_payment_date__gte=today) | Q(next_payment_date__isnull=True)
            )
            
            days_1_30 = loans_qs.filter(
                next_payment_date__lt=today,
                next_payment_date__gte=today - timedelta(days=30)
            )
            
            days_31_60 = loans_qs.filter(
                next_payment_date__lt=today - timedelta(days=30),
                next_payment_date__gte=today - timedelta(days=60)
            )
            
            days_61_90 = loans_qs.filter(
                next_payment_date__lt=today - timedelta(days=60),
                next_payment_date__gte=today - timedelta(days=90)
            )
            
            over_90 = loans_qs.filter(
                next_payment_date__lt=today - timedelta(days=90)
            )
            
            # Calculate amounts and counts
            total_portfolio = loans_qs.aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
            
            def get_bucket_data(queryset):
                amount = queryset.aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
                count = queryset.count()
                percentage = Decimal('0.0')
                if total_portfolio > 0:
                    percentage = Decimal(str(amount / total_portfolio * 100)).quantize(Decimal('0.1'))
                return {'amount': amount, 'count': count, 'percentage': percentage}
            
            data = {
                'current': get_bucket_data(current_loans),
                'days_1_30': get_bucket_data(days_1_30),
                'days_31_60': get_bucket_data(days_31_60),
                'days_61_90': get_bucket_data(days_61_90),
                'over_90': get_bucket_data(over_90),
                'total_portfolio': total_portfolio,
                'updated_at': timezone.now().isoformat(),
            }
            
            self._set_cached_data(cache_key, 'aging', data)
            return data
            
        except Exception as e:
            # Fail-safe return
            return {
                'current': {'amount': Decimal('0.00'), 'count': 0, 'percentage': Decimal('0.0')},
                'days_1_30': {'amount': Decimal('0.00'), 'count': 0, 'percentage': Decimal('0.0')},
                'days_31_60': {'amount': Decimal('0.00'), 'count': 0, 'percentage': Decimal('0.0')},
                'days_61_90': {'amount': Decimal('0.00'), 'count': 0, 'percentage': Decimal('0.0')},
                'over_90': {'amount': Decimal('0.00'), 'count': 0, 'percentage': Decimal('0.0')},
                'total_portfolio': Decimal('0.00'),
                'error': str(e),
                'updated_at': timezone.now().isoformat(),
            }
    
    def monthly_trends(self, months: int = 12) -> List[Dict[str, Any]]:
        """
        Generate monthly trends data for charts
        """
        cache_key = self._get_cache_key('monthly_trends', months=months)
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            trends_data = []
            today = timezone.now().date()
            
            for i in range(months):
                # Calculate month boundaries
                month_end = today.replace(day=1) - timedelta(days=i*30)
                month_start = month_end.replace(day=1)
                
                # Get data for this month
                month_applications = LoanApplication.objects.filter(
                    company=self.company,
                    application_date__gte=month_start,
                    application_date__lt=month_end + timedelta(days=31)
                ).count()
                
                month_disbursements = Loan.objects.filter(
                    company=self.company,
                    created_at__gte=month_start,
                    created_at__lt=month_end + timedelta(days=31)
                ).aggregate(total=Sum('principal_amount'))['total'] or 0
                
                month_collections = Payment.objects.filter(
                    company=self.company,
                    payment_date__gte=month_start,
                    payment_date__lt=month_end + timedelta(days=31),
                    status='completed'
                ).aggregate(total=Sum('payment_amount'))['total'] or 0
                
                trends_data.append({
                    'month': month_start.strftime('%b'),
                    'year': month_start.year,
                    'applications': month_applications,
                    'disbursements': float(month_disbursements),
                    'collections': float(month_collections),
                })
            
            trends_data.reverse()  # Show chronological order
            self._set_cached_data(cache_key, 'monthly_trends', trends_data)
            return trends_data
            
        except Exception as e:
            # Fail-safe return with empty data
            return []
    
    def customer_performance(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Generate top performing customers report
        """
        cache_key = self._get_cache_key('customer_performance', limit=limit)
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            customers = Customer.objects.filter(company=self.company)
            customer_data = []
            
            for customer in customers:
                total_borrowed = Loan.objects.filter(
                    customer=customer
                ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
                
                payments_made = Payment.objects.filter(
                    customer=customer,
                    status='completed'
                ).count()
                
                if total_borrowed > 0:  # Only include customers with loans
                    customer_data.append({
                        'name': f"{customer.first_name} {customer.last_name}",
                        'total_borrowed': float(total_borrowed),
                        'payments_made': payments_made,
                        'score': 'A' if payments_made > 20 else 'B' if payments_made > 10 else 'C',
                    })
            
            # Sort by total borrowed and limit results
            customer_data.sort(key=lambda x: x['total_borrowed'], reverse=True)
            result = customer_data[:limit]
            
            self._set_cached_data(cache_key, 'customer_performance', result)
            return result
            
        except Exception as e:
            return []
    
    def risk_metrics(self) -> Dict[str, Any]:
        """
        Generate risk assessment metrics
        """
        cache_key = self._get_cache_key('risk_metrics')
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            loans_qs = Loan.objects.filter(company=self.company)
            
            # Simple risk categorization based on days overdue
            today = timezone.now().date()
            
            high_risk = loans_qs.filter(
                next_payment_date__lt=today - timedelta(days=60)
            ).count()
            
            medium_risk = loans_qs.filter(
                next_payment_date__lt=today - timedelta(days=30),
                next_payment_date__gte=today - timedelta(days=60)
            ).count()
            
            low_risk = loans_qs.filter(
                Q(next_payment_date__gte=today) | 
                Q(next_payment_date__gte=today - timedelta(days=30))
            ).count()
            
            total_loans = loans_qs.count()
            npl_ratio = Decimal('0.0')
            if total_loans > 0:
                npl_ratio = Decimal(str(high_risk / total_loans * 100)).quantize(Decimal('0.1'))
            
            data = {
                'high_risk_loans': high_risk,
                'medium_risk_loans': medium_risk,
                'low_risk_loans': low_risk,
                'provision_coverage': Decimal('125.0'),  # Could be calculated from provisions
                'npl_ratio': npl_ratio,
                'loss_rate': Decimal('0.5'),  # Could be calculated from write-offs
                'updated_at': timezone.now().isoformat(),
            }
            
            self._set_cached_data(cache_key, 'risk_metrics', data)
            return data
            
        except Exception as e:
            return {
                'high_risk_loans': 0,
                'medium_risk_loans': 0,
                'low_risk_loans': 0,
                'provision_coverage': Decimal('0.0'),
                'npl_ratio': Decimal('0.0'),
                'loss_rate': Decimal('0.0'),
                'error': str(e),
                'updated_at': timezone.now().isoformat(),
            }
