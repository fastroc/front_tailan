"""
Django Admin Commands for Payment Data Cleanup
Provides management commands for data analysis and cleanup
"""

from django.core.management.base import BaseCommand, CommandError
from company.models import Company
from loans_payments.services import DuplicateDetectionService, PaymentDataCleanupService
from loans_payments.models import Payment
import json


class Command(BaseCommand):
    help = 'Analyze payment data quality and provide cleanup recommendations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Company ID to analyze (required)',
            required=True
        )
        parser.add_argument(
            '--action',
            type=str,
            choices=['analyze', 'cleanup', 'fresh-start', 'duplicates'],
            default='analyze',
            help='Action to perform: analyze, cleanup, fresh-start, or duplicates'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            default=True,
            help='Create backup before cleanup (default: True)'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Save results to JSON file'
        )
    
    def handle(self, *args, **options):
        try:
            company = Company.objects.get(id=options['company_id'])
            self.stdout.write(f"Processing company: {company.name}")
            
            cleanup_service = PaymentDataCleanupService(company=company)
            duplicate_service = DuplicateDetectionService(company=company)
            
            if options['action'] == 'analyze':
                self.analyze_data_quality(cleanup_service, options)
            elif options['action'] == 'cleanup':
                self.cleanup_data(cleanup_service, options)
            elif options['action'] == 'fresh-start':
                self.fresh_start(cleanup_service, options)
            elif options['action'] == 'duplicates':
                self.find_duplicates(duplicate_service, company, options)
                
        except Company.DoesNotExist:
            raise CommandError(f'Company with ID {options["company_id"]} does not exist')
        except Exception as e:
            raise CommandError(f'Command failed: {str(e)}')
    
    def analyze_data_quality(self, cleanup_service, options):
        """Analyze and report data quality issues"""
        self.stdout.write("\n🔍 ANALYZING PAYMENT DATA QUALITY...")
        
        report = cleanup_service.analyze_data_quality()
        
        # Display summary
        self.stdout.write("\n📊 SUMMARY:")
        self.stdout.write(f"  Total payments: {report['total_payments']}")
        self.stdout.write(f"  Data quality score: {report['data_integrity']['score']:.1%}")
        self.stdout.write(f"  Issues found: {report['data_integrity']['issues_count']}")
        self.stdout.write(f"  Critical issues: {report['data_integrity']['critical_issues']}")
        
        # Display issues by category
        if report['issues_found']:
            self.stdout.write("\n⚠️  ISSUES BY CATEGORY:")
            for issue_type, count in report['issues_found'].items():
                self.stdout.write(f"  {issue_type.replace('_', ' ').title()}: {count}")
        
        # Display recommendations
        if report['recommendations']:
            self.stdout.write("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                self.stdout.write(f"  • {rec}")
        
        # Show detailed issues
        if report['cleanup_candidates']['suspicious_duplicates']:
            self.stdout.write(f"\n🔄 SUSPICIOUS DUPLICATES ({len(report['cleanup_candidates']['suspicious_duplicates'])}):")
            for dup in report['cleanup_candidates']['suspicious_duplicates'][:5]:  # Show first 5
                self.stdout.write(f"  • {dup['payment1_id']} ↔ {dup['payment2_id']} "
                                f"(Confidence: {dup['confidence']:.1%}, "
                                f"Loan: {dup['loan_number']}, "
                                f"Reasons: {', '.join(dup['reasons'])})")
            if len(report['cleanup_candidates']['suspicious_duplicates']) > 5:
                remaining = len(report['cleanup_candidates']['suspicious_duplicates']) - 5
                self.stdout.write(f"  ... and {remaining} more duplicates")
        
        # Save to file if requested
        if options.get('output_file'):
            with open(options['output_file'], 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.stdout.write(f"\n💾 Report saved to: {options['output_file']}")
    
    def cleanup_data(self, cleanup_service, options):
        """Perform data cleanup"""
        if options.get('dry_run'):
            self.stdout.write("\n🧹 DRY RUN - SHOWING CLEANUP ACTIONS...")
        else:
            self.stdout.write("\n🧹 PERFORMING DATA CLEANUP...")
        
        # First analyze
        report = cleanup_service.analyze_data_quality()
        
        if report['data_integrity']['issues_count'] == 0:
            self.stdout.write("✅ No data quality issues found - no cleanup needed")
            return
        
        if options.get('dry_run'):
            self.stdout.write(f"\nWould clean up {report['data_integrity']['issues_count']} issues:")
            
            for issue_type, candidates in report['cleanup_candidates'].items():
                if candidates:
                    self.stdout.write(f"\n  {issue_type.replace('_', ' ').title()}:")
                    for candidate in candidates[:3]:  # Show first 3
                        if 'payment_id' in candidate:
                            self.stdout.write(f"    • Would remove payment: {candidate['payment_id']}")
                        elif 'payment1_id' in candidate:
                            self.stdout.write(f"    • Would review duplicate: {candidate['payment1_id']} ↔ {candidate['payment2_id']}")
        else:
            # Perform actual cleanup
            if options.get('backup', True):
                self.stdout.write("📦 Creating backup before cleanup...")
            
            cleanup_results = cleanup_service.cleanup_invalid_data(
                report, 
                create_backup=options.get('backup', True)
            )
            
            self.stdout.write("\n✅ CLEANUP COMPLETED:")
            self.stdout.write(f"  Payments removed: {cleanup_results['removed_payments']}")
            self.stdout.write(f"  Payments updated: {cleanup_results['updated_payments']}")
            
            if cleanup_results['errors']:
                self.stdout.write(f"  ❌ Errors: {len(cleanup_results['errors'])}")
                for error in cleanup_results['errors']:
                    self.stdout.write(f"    • {error}")
    
    def fresh_start(self, cleanup_service, options):
        """Prepare for fresh start"""
        if options.get('dry_run'):
            self.stdout.write("\n🔄 DRY RUN - FRESH START PREPARATION...")
            
            report = cleanup_service.analyze_data_quality()
            self.stdout.write("Current state:")
            self.stdout.write(f"  • {report['total_payments']} payments")
            self.stdout.write(f"  • {report['data_integrity']['issues_count']} issues")
            self.stdout.write(f"  • Quality score: {report['data_integrity']['score']:.1%}")
            
            self.stdout.write("\nFresh start would:")
            self.stdout.write("  • Create backup of current data")
            self.stdout.write(f"  • Clean up {report['data_integrity']['issues_count']} issues")
            self.stdout.write("  • Prepare system for bulk upload")
            
        else:
            self.stdout.write("\n🔄 PREPARING FRESH START...")
            
            fresh_results = cleanup_service.prepare_fresh_start()
            
            if fresh_results['system_ready']:
                self.stdout.write("✅ FRESH START PREPARATION COMPLETED")
                self.stdout.write(f"  • Backup created: {fresh_results['backup_created']}")
                self.stdout.write(f"  • Data analyzed: {fresh_results['data_analyzed']}")
                self.stdout.write(f"  • Cleanup performed: {fresh_results['cleanup_performed']}")
                self.stdout.write(f"  • Final quality score: {fresh_results['summary']['final_quality_score']:.1%}")
                self.stdout.write("  • Ready for bulk upload: ✅")
            else:
                self.stdout.write("⚠️ FRESH START PREPARATION INCOMPLETE")
                if 'error' in fresh_results:
                    self.stdout.write(f"  Error: {fresh_results['error']}")
    
    def find_duplicates(self, duplicate_service, company, options):
        """Find and analyze duplicate payments"""
        self.stdout.write("\n🔄 SEARCHING FOR DUPLICATE PAYMENTS...")
        
        all_payments = Payment.objects.filter(company=company).order_by('payment_date')
        
        if not all_payments.exists():
            self.stdout.write("No payments found for analysis")
            return
        
        # Analyze payments for duplicates
        suspected_duplicates = []
        
        for payment in all_payments:
            duplicate_check = duplicate_service.check_for_duplicates(
                payment.loan.loan_number,
                payment.payment_amount,
                payment.payment_date,
                payment.customer.first_name if hasattr(payment.customer, 'first_name') else '',
                payment.reference_number
            )
            
            if duplicate_check['is_duplicate'] or duplicate_check['confidence'] > 0.4:
                suspected_duplicates.append({
                    'payment': payment,
                    'duplicate_check': duplicate_check
                })
        
        if suspected_duplicates:
            self.stdout.write(f"\n🔄 FOUND {len(suspected_duplicates)} SUSPECTED DUPLICATES:")
            
            for item in suspected_duplicates:
                payment = item['payment']
                check = item['duplicate_check']
                
                self.stdout.write(f"\n  Payment: {payment.payment_id}")
                self.stdout.write(f"    Loan: {payment.loan.loan_number}")
                self.stdout.write(f"    Amount: ${payment.payment_amount}")
                self.stdout.write(f"    Date: {payment.payment_date}")
                self.stdout.write(f"    Confidence: {check['confidence']:.1%}")
                self.stdout.write(f"    Recommendation: {check['recommendation']}")
                
                if check['reasons']:
                    self.stdout.write(f"    Reasons: {', '.join(check['reasons'])}")
                
                if check['matching_payments'].exists():
                    matching_ids = [p.payment_id for p in check['matching_payments']]
                    self.stdout.write(f"    Matches: {', '.join(matching_ids)}")
        else:
            self.stdout.write("✅ No duplicate payments found")
        
        if options.get('output_file'):
            duplicate_data = [
                {
                    'payment_id': item['payment'].payment_id,
                    'loan_number': item['payment'].loan.loan_number,
                    'amount': str(item['payment'].payment_amount),
                    'date': str(item['payment'].payment_date),
                    'confidence': item['duplicate_check']['confidence'],
                    'recommendation': item['duplicate_check']['recommendation'],
                    'reasons': item['duplicate_check']['reasons']
                }
                for item in suspected_duplicates
            ]
            
            with open(options['output_file'], 'w') as f:
                json.dump(duplicate_data, f, indent=2)
            
            self.stdout.write(f"\n💾 Duplicate analysis saved to: {options['output_file']}")
