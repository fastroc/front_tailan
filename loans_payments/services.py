"""
Advanced Payment Processing Services with Duplicate Prevention
Provides comprehensive duplicate detection and data cleanup for loan payments
"""
from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """
    Comprehensive duplicate detection service for payment processing
    Prevents duplicate payments with multiple validation strategies
    """
    
    def __init__(self, company=None, strict_mode=True):
        self.company = company
        self.strict_mode = strict_mode
        self.duplicate_reasons = []
    
    def check_for_duplicates(self, loan_id, payment_amount, payment_date, 
                           customer_first_name=None, reference_number=None, 
                           tolerance_days=3, tolerance_amount=0.01):
        """
        Check for potential duplicate payments using multiple criteria
        
        Args:
            loan_id: Loan number to check
            payment_amount: Payment amount to validate
            payment_date: Date of payment
            customer_first_name: Optional customer validation
            reference_number: Optional reference number check
            tolerance_days: Days tolerance for date matching (default: 3)
            tolerance_amount: Amount tolerance for matching (default: $0.01)
            
        Returns:
            dict: {
                'is_duplicate': bool,
                'confidence': float (0.0-1.0),
                'reasons': list,
                'matching_payments': queryset,
                'recommendation': str
            }
        """
        from .models import Payment
        from loans_core.models import Loan
        
        result = {
            'is_duplicate': False,
            'confidence': 0.0,
            'reasons': [],
            'matching_payments': Payment.objects.none(),
            'recommendation': 'ACCEPT'
        }
        
        # Initialize confidence score
        confidence_score = 0.0
        
        # Get loan object
        try:
            loan = Loan.objects.get(
                company=self.company,
                loan_number=loan_id
            )
        except Loan.DoesNotExist:
            result['reasons'].append(f'Loan {loan_id} not found')
            result['recommendation'] = 'REJECT'
            return result
        
        # Convert inputs
        amount = Decimal(str(payment_amount))
        if isinstance(payment_date, str):
            payment_date = self._parse_date(payment_date)
        
        # Define search criteria
        date_start = payment_date - timedelta(days=tolerance_days)
        date_end = payment_date + timedelta(days=tolerance_days)
        amount_min = amount - Decimal(str(tolerance_amount))
        amount_max = amount + Decimal(str(tolerance_amount))
        
        # Search for potential duplicates
        potential_duplicates = Payment.objects.filter(
            company=self.company,
            loan=loan,
            payment_date__range=[date_start, date_end],
            payment_amount__range=[amount_min, amount_max],
            status__in=['pending', 'processing', 'completed']  # Exclude failed/cancelled
        )
        
        if potential_duplicates.exists():
            result['matching_payments'] = potential_duplicates
            
            for payment in potential_duplicates:
                match_reasons = []
                match_confidence = 0.0
                
                # Exact amount match
                if payment.payment_amount == amount:
                    match_reasons.append('Exact amount match')
                    match_confidence += 0.4
                elif abs(payment.payment_amount - amount) <= Decimal('0.01'):
                    match_reasons.append('Near exact amount match')
                    match_confidence += 0.3
                
                # Exact date match
                if payment.payment_date == payment_date:
                    match_reasons.append('Exact date match')
                    match_confidence += 0.4
                elif abs((payment.payment_date - payment_date).days) <= 1:
                    match_reasons.append('Adjacent date match')
                    match_confidence += 0.2
                
                # Customer validation if provided
                if customer_first_name:
                    if loan.customer.first_name.upper() == customer_first_name.upper():
                        match_confidence += 0.1
                    else:
                        match_reasons.append('Customer name mismatch - possible data error')
                        match_confidence -= 0.2
                
                # Reference number check
                if reference_number and payment.reference_number:
                    if payment.reference_number == reference_number:
                        match_reasons.append('Identical reference number')
                        match_confidence += 0.3
                
                # Payment method proximity (same day, similar amounts often same method)
                if (payment.payment_date == payment_date and 
                    abs(payment.payment_amount - amount) < Decimal('1.00')):
                    match_confidence += 0.1
                
                confidence_score = max(confidence_score, match_confidence)
                result['reasons'].extend([f"Payment {payment.payment_id}: {', '.join(match_reasons)}"])
        
        # Determine final result
        result['confidence'] = confidence_score
        
        if confidence_score >= 0.8:
            result['is_duplicate'] = True
            result['recommendation'] = 'REJECT'
        elif confidence_score >= 0.6:
            result['is_duplicate'] = True
            result['recommendation'] = 'REVIEW'
        elif confidence_score >= 0.4:
            result['recommendation'] = 'CAUTION'
        else:
            result['recommendation'] = 'ACCEPT'
        
        return result
    
    def generate_payment_fingerprint(self, loan_id, amount, date, customer_name=''):
        """
        Generate unique fingerprint for payment to detect exact duplicates
        """
        fingerprint_data = f"{loan_id}|{amount}|{date}|{customer_name.upper()}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def batch_duplicate_check(self, payment_data_list):
        """
        Check list of payments for duplicates against existing and within batch
        
        Args:
            payment_data_list: List of dicts with payment information
            
        Returns:
            dict: {
                'clean_payments': list,
                'duplicates_found': list,
                'internal_duplicates': list,
                'summary': dict
            }
        """
        results = {
            'clean_payments': [],
            'duplicates_found': [],
            'internal_duplicates': [],
            'summary': {
                'total_processed': 0,
                'clean_count': 0,
                'external_duplicates': 0,
                'internal_duplicates': 0,
                'rejected_count': 0
            }
        }
        
        fingerprints_seen = set()
        
        for idx, payment_data in enumerate(payment_data_list):
            results['summary']['total_processed'] += 1
            
            try:
                # Generate fingerprint for internal duplicate detection
                fingerprint = self.generate_payment_fingerprint(
                    payment_data.get('loan_number', ''),
                    payment_data.get('payment_amount', 0),
                    payment_data.get('payment_date', ''),
                    payment_data.get('customer_first_name', '')
                )
                
                # Check for internal duplicates (within this batch)
                if fingerprint in fingerprints_seen:
                    payment_data['row_number'] = idx + 1
                    payment_data['duplicate_type'] = 'INTERNAL'
                    payment_data['reason'] = 'Duplicate within batch data'
                    results['internal_duplicates'].append(payment_data)
                    results['summary']['internal_duplicates'] += 1
                    continue
                
                fingerprints_seen.add(fingerprint)
                
                # Check against existing payments
                duplicate_check = self.check_for_duplicates(
                    payment_data.get('loan_number'),
                    payment_data.get('payment_amount'),
                    payment_data.get('payment_date'),
                    payment_data.get('customer_first_name'),
                    payment_data.get('reference_number', '')
                )
                
                payment_data['row_number'] = idx + 1
                payment_data['duplicate_check'] = duplicate_check
                
                if duplicate_check['recommendation'] == 'REJECT':
                    payment_data['duplicate_type'] = 'EXTERNAL'
                    results['duplicates_found'].append(payment_data)
                    results['summary']['external_duplicates'] += 1
                elif duplicate_check['recommendation'] in ['REVIEW', 'CAUTION']:
                    payment_data['needs_review'] = True
                    results['clean_payments'].append(payment_data)
                    results['summary']['clean_count'] += 1
                else:
                    results['clean_payments'].append(payment_data)
                    results['summary']['clean_count'] += 1
                    
            except Exception as e:
                payment_data['row_number'] = idx + 1
                payment_data['error'] = str(e)
                payment_data['duplicate_type'] = 'ERROR'
                payment_data['reason'] = f'Processing error: {str(e)}'
                results['duplicates_found'].append(payment_data)
                results['summary']['rejected_count'] += 1
        
        return results
    
    def _parse_date(self, date_str):
        """Parse date string in multiple formats"""
        formats = [
            '%Y-%m-%d', '%Y.%m.%d', '%m/%d/%Y', 
            '%d/%m/%Y', '%d.%m.%Y', '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f'Unable to parse date: {date_str}')


class PaymentDataCleanupService:
    """
    Service for cleaning up incorrect payment data and preparing for fresh starts
    """
    
    def __init__(self, company=None):
        self.company = company
        self.cleanup_log = []
    
    def analyze_data_quality(self):
        """
        Analyze payment data quality and identify potential issues
        
        Returns comprehensive data quality report
        """
        from .models import Payment
        from loans_core.models import Loan
        
        report = {
            'total_payments': 0,
            'issues_found': {},
            'recommendations': [],
            'cleanup_candidates': {
                'suspicious_duplicates': [],
                'invalid_amounts': [],
                'future_dates': [],
                'orphaned_payments': [],
                'inconsistent_allocations': []
            },
            'data_integrity': {
                'score': 0.0,
                'issues_count': 0,
                'critical_issues': 0
            }
        }
        
        # Get all payments for company
        all_payments = Payment.objects.filter(company=self.company)
        report['total_payments'] = all_payments.count()
        
        if report['total_payments'] == 0:
            report['data_integrity']['score'] = 1.0
            report['recommendations'].append('No payment data found - ready for fresh start')
            return report
        
        issues_count = 0
        critical_issues = 0
        
        # 1. Check for suspicious duplicates
        suspicious_duplicates = self._find_suspicious_duplicates(all_payments)
        if suspicious_duplicates:
            report['cleanup_candidates']['suspicious_duplicates'] = suspicious_duplicates
            report['issues_found']['suspicious_duplicates'] = len(suspicious_duplicates)
            issues_count += len(suspicious_duplicates)
            critical_issues += len([d for d in suspicious_duplicates if d['confidence'] > 0.8])
        
        # 2. Check for invalid amounts
        invalid_amounts = all_payments.filter(
            models.Q(payment_amount__lte=0) |
            models.Q(payment_amount__gt=100000)  # Suspiciously high
        )
        if invalid_amounts.exists():
            report['cleanup_candidates']['invalid_amounts'] = [
                {
                    'payment_id': p.payment_id,
                    'amount': p.payment_amount,
                    'loan': p.loan.loan_number,
                    'date': p.payment_date
                }
                for p in invalid_amounts
            ]
            report['issues_found']['invalid_amounts'] = invalid_amounts.count()
            issues_count += invalid_amounts.count()
            critical_issues += invalid_amounts.count()
        
        # 3. Check for future dates
        future_payments = all_payments.filter(
            payment_date__gt=timezone.now().date()
        )
        if future_payments.exists():
            report['cleanup_candidates']['future_dates'] = [
                {
                    'payment_id': p.payment_id,
                    'date': p.payment_date,
                    'loan': p.loan.loan_number,
                    'amount': p.payment_amount
                }
                for p in future_payments
            ]
            report['issues_found']['future_dates'] = future_payments.count()
            issues_count += future_payments.count()
        
        # 4. Check for orphaned payments (loans no longer exist)
        loan_ids = set(Loan.objects.filter(company=self.company).values_list('id', flat=True))
        orphaned_payments = [
            p for p in all_payments 
            if p.loan_id not in loan_ids
        ]
        if orphaned_payments:
            report['cleanup_candidates']['orphaned_payments'] = [
                {
                    'payment_id': p.payment_id,
                    'loan_id': p.loan_id,
                    'amount': p.payment_amount,
                    'date': p.payment_date
                }
                for p in orphaned_payments
            ]
            report['issues_found']['orphaned_payments'] = len(orphaned_payments)
            issues_count += len(orphaned_payments)
            critical_issues += len(orphaned_payments)
        
        # 5. Check allocation consistency
        payments_with_allocations = all_payments.filter(allocations__isnull=False).distinct()
        for payment in payments_with_allocations:
            allocation_total = payment.allocations.aggregate(
                total=models.Sum('allocation_amount')
            )['total'] or Decimal('0.00')
            
            if abs(allocation_total - payment.payment_amount) > Decimal('0.01'):
                report['cleanup_candidates']['inconsistent_allocations'].append({
                    'payment_id': payment.payment_id,
                    'payment_amount': payment.payment_amount,
                    'allocation_total': allocation_total,
                    'difference': payment.payment_amount - allocation_total
                })
                issues_count += 1
        
        # Calculate data integrity score
        if report['total_payments'] > 0:
            clean_payments = report['total_payments'] - issues_count
            report['data_integrity']['score'] = max(0.0, clean_payments / report['total_payments'])
        
        report['data_integrity']['issues_count'] = issues_count
        report['data_integrity']['critical_issues'] = critical_issues
        
        # Generate recommendations
        if report['data_integrity']['score'] < 0.7:
            report['recommendations'].append('CRITICAL: Data quality is poor - recommend full cleanup')
        elif report['data_integrity']['score'] < 0.9:
            report['recommendations'].append('WARNING: Some data issues detected - selective cleanup recommended')
        else:
            report['recommendations'].append('GOOD: Data quality is acceptable - minor cleanup may be beneficial')
        
        if critical_issues > 0:
            report['recommendations'].append(f'Address {critical_issues} critical issues before proceeding')
        
        if len(report['cleanup_candidates']['suspicious_duplicates']) > 0:
            report['recommendations'].append('Review and remove suspicious duplicate payments')
        
        return report
    
    def _find_suspicious_duplicates(self, payments_queryset):
        """Find potentially duplicate payments using advanced analysis"""
        duplicates = []
        
        # Group by loan and look for same-day payments
        loan_groups = {}
        for payment in payments_queryset.select_related('loan'):
            loan_id = payment.loan.loan_number
            if loan_id not in loan_groups:
                loan_groups[loan_id] = []
            loan_groups[loan_id].append(payment)
        
        # Analyze each loan's payments
        for loan_id, loan_payments in loan_groups.items():
            # Sort by date
            loan_payments.sort(key=lambda p: p.payment_date)
            
            # Look for suspicious patterns
            for i, payment in enumerate(loan_payments):
                for j in range(i + 1, len(loan_payments)):
                    other_payment = loan_payments[j]
                    
                    # Skip if dates are too far apart
                    days_diff = (other_payment.payment_date - payment.payment_date).days
                    if days_diff > 7:
                        break  # Sorted by date, so no need to check further
                    
                    # Calculate similarity
                    amount_diff = abs(payment.payment_amount - other_payment.payment_amount)
                    confidence = 0.0
                    reasons = []
                    
                    if days_diff == 0:  # Same day
                        confidence += 0.5
                        reasons.append('Same day')
                        
                        if amount_diff == 0:  # Exact amount
                            confidence += 0.4
                            reasons.append('Exact amount')
                        elif amount_diff < Decimal('1.00'):
                            confidence += 0.2
                            reasons.append('Similar amount')
                    
                    elif days_diff <= 2:  # Adjacent days
                        confidence += 0.3
                        reasons.append(f'{days_diff} day(s) apart')
                        
                        if amount_diff == 0:
                            confidence += 0.3
                            reasons.append('Exact amount')
                    
                    # Check for exact matches in reference numbers
                    if (payment.reference_number and other_payment.reference_number and
                        payment.reference_number == other_payment.reference_number):
                        confidence += 0.3
                        reasons.append('Same reference number')
                    
                    if confidence >= 0.6:  # Threshold for suspicious
                        duplicates.append({
                            'payment1_id': payment.payment_id,
                            'payment2_id': other_payment.payment_id,
                            'loan_number': loan_id,
                            'confidence': confidence,
                            'reasons': reasons,
                            'payment1_date': payment.payment_date,
                            'payment2_date': other_payment.payment_date,
                            'payment1_amount': payment.payment_amount,
                            'payment2_amount': other_payment.payment_amount,
                            'days_apart': days_diff
                        })
        
        return duplicates
    
    def create_backup_before_cleanup(self, backup_name=None):
        """
        Create backup of payment data before cleanup
        """
        if not backup_name:
            backup_name = f"payment_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        from django.core.management import call_command
        import os
        
        backup_file = f"D:\\Again\\backups\\{backup_name}.json"
        
        # Create backup directory if it doesn't exist
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        
        try:
            # Export payment data
            with open(backup_file, 'w') as f:
                call_command('dumpdata', 'loans_payments', stdout=f, indent=2)
            
            self.cleanup_log.append(f"Backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.cleanup_log.append(f"Backup failed: {str(e)}")
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def cleanup_invalid_data(self, issues_report, create_backup=True):
        """
        Clean up invalid payment data based on analysis report
        """
        from .models import Payment
        
        if create_backup:
            self.create_backup_before_cleanup()
        
        cleanup_results = {
            'removed_payments': 0,
            'updated_payments': 0,
            'errors': [],
            'details': []
        }
        
        with transaction.atomic():
            try:
                # 1. Remove payments with invalid amounts
                invalid_amounts = issues_report['cleanup_candidates'].get('invalid_amounts', [])
                for invalid_payment in invalid_amounts:
                    try:
                        payment = Payment.objects.get(
                            company=self.company,
                            payment_id=invalid_payment['payment_id']
                        )
                        payment.delete()
                        cleanup_results['removed_payments'] += 1
                        cleanup_results['details'].append(f"Removed invalid amount: {invalid_payment['payment_id']}")
                    except Payment.DoesNotExist:
                        continue
                
                # 2. Remove orphaned payments
                orphaned_payments = issues_report['cleanup_candidates'].get('orphaned_payments', [])
                for orphaned in orphaned_payments:
                    try:
                        payment = Payment.objects.get(
                            company=self.company,
                            payment_id=orphaned['payment_id']
                        )
                        payment.delete()
                        cleanup_results['removed_payments'] += 1
                        cleanup_results['details'].append(f"Removed orphaned payment: {orphaned['payment_id']}")
                    except Payment.DoesNotExist:
                        continue
                
                # 3. Fix future dates (set to today)
                future_dates = issues_report['cleanup_candidates'].get('future_dates', [])
                for future_payment in future_dates:
                    try:
                        payment = Payment.objects.get(
                            company=self.company,
                            payment_id=future_payment['payment_id']
                        )
                        payment.payment_date = timezone.now().date()
                        payment.save()
                        cleanup_results['updated_payments'] += 1
                        cleanup_results['details'].append(f"Fixed future date: {future_payment['payment_id']}")
                    except Payment.DoesNotExist:
                        continue
                
                self.cleanup_log.append(f"Cleanup completed: {cleanup_results}")
                
            except Exception as e:
                cleanup_results['errors'].append(str(e))
                self.cleanup_log.append(f"Cleanup error: {str(e)}")
                raise
        
        return cleanup_results
    
    def prepare_fresh_start(self):
        """
        Prepare system for fresh bulk upload start
        """
        fresh_start_results = {
            'backup_created': False,
            'data_analyzed': False,
            'cleanup_performed': False,
            'system_ready': False,
            'summary': {}
        }
        
        try:
            # 1. Create backup
            self.create_backup_before_cleanup("fresh_start_backup")
            fresh_start_results['backup_created'] = True
            
            # 2. Analyze current data
            data_report = self.analyze_data_quality()
            fresh_start_results['data_analyzed'] = True
            fresh_start_results['summary']['current_payments'] = data_report['total_payments']
            fresh_start_results['summary']['issues_found'] = data_report['data_integrity']['issues_count']
            
            # 3. Perform cleanup if needed
            if data_report['data_integrity']['issues_count'] > 0:
                cleanup_results = self.cleanup_invalid_data(data_report, create_backup=False)
                fresh_start_results['cleanup_performed'] = True
                fresh_start_results['summary']['cleanup_results'] = cleanup_results
            
            # 4. Final verification
            final_report = self.analyze_data_quality()
            fresh_start_results['summary']['final_payments'] = final_report['total_payments']
            fresh_start_results['summary']['final_quality_score'] = final_report['data_integrity']['score']
            
            if final_report['data_integrity']['score'] >= 0.9:
                fresh_start_results['system_ready'] = True
            
            self.cleanup_log.append("Fresh start preparation completed")
            
        except Exception as e:
            fresh_start_results['error'] = str(e)
            self.cleanup_log.append(f"Fresh start preparation failed: {str(e)}")
        
        return fresh_start_results
