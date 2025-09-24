#!/usr/bin/env python
"""
Financial Rules Test Runner

Comprehensive test runner for the financial rules system.
Runs all test suites and provides detailed reporting.
"""

import os
import sys
import django
from io import StringIO

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test.utils import get_runner
from django.conf import settings
from django.core.management import call_command


def run_financial_rules_tests():
    """Run comprehensive test suite for financial rules"""
    
    print("🧪 Financial Rules Test Suite")
    print("=" * 50)
    
    # Setup test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True)
    
    # Test modules to run
    test_modules = [
        'financial_rules.tests.test_models',
        'financial_rules.tests.test_engines', 
        'financial_rules.tests.test_views',
    ]
    
    print(f"📋 Running {len(test_modules)} test modules...")
    print()
    
    # Run tests
    failures = test_runner.run_tests(test_modules)
    
    # Summary
    if failures:
        print(f"\n❌ {failures} test(s) failed!")
        return False
    else:
        print(f"\n✅ All tests passed!")
        return True


def run_coverage_report():
    """Run test coverage analysis"""
    print("\n📊 Test Coverage Analysis")
    print("-" * 30)
    
    try:
        import coverage
        
        # Create coverage instance
        cov = coverage.Coverage(source=['financial_rules'])
        cov.start()
        
        # Run tests with coverage
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=0, interactive=False)
        
        test_modules = [
            'financial_rules.tests.test_models',
            'financial_rules.tests.test_engines', 
            'financial_rules.tests.test_views',
        ]
        
        failures = test_runner.run_tests(test_modules)
        
        cov.stop()
        cov.save()
        
        # Generate report
        print("\n📈 Coverage Report:")
        cov.report(show_missing=True)
        
        # Generate HTML report
        html_dir = os.path.join(os.path.dirname(__file__), 'coverage_html')
        cov.html_report(directory=html_dir)
        print(f"\n📄 HTML coverage report generated: {html_dir}/index.html")
        
        return failures == 0
        
    except ImportError:
        print("⚠️ Coverage module not installed. Install with: pip install coverage")
        return True


def run_performance_tests():
    """Run basic performance tests"""
    print("\n⚡ Performance Tests")
    print("-" * 20)
    
    import time
    from decimal import Decimal
    from company.models import Company
    from financial_rules.models import BaseFinancialRule, RuleAction
    from financial_rules.engines.base_engine import RuleEngineFactory
    
    try:
        # Get test company
        company = Company.objects.first()
        if not company:
            print("⚠️ No company found for performance tests")
            return True
            
        # Create a simple rule for testing
        rule = BaseFinancialRule.objects.create(
            company=company,
            name='Performance Test Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Test Payment',
            account_code='4200',
            allocation_type='percentage',
            value=Decimal('100'),
            sequence=1
        )
        
        # Test rule engine performance
        engine = RuleEngineFactory.create_engine(company.id, ['loan_payment'])
        
        transaction_data = {
            'customer_name': 'Performance Test Customer',
            'transaction_amount': Decimal('100.00'),
            'transaction_description': 'Performance test'
        }
        
        # Warm up
        engine.evaluate_transaction(transaction_data, ['loan_payment'])
        
        # Performance test
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            result = engine.evaluate_transaction(transaction_data, ['loan_payment'])
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = (total_time / iterations) * 1000  # Convert to milliseconds
        
        print(f"📊 Rule evaluation performance:")
        print(f"   - Iterations: {iterations}")
        print(f"   - Total time: {total_time:.3f} seconds")
        print(f"   - Average time: {avg_time:.2f} ms per evaluation")
        print(f"   - Throughput: {iterations/total_time:.0f} evaluations/second")
        
        # Cleanup
        rule.delete()
        
        # Performance benchmarks
        if avg_time < 10:
            print("✅ Excellent performance (< 10ms)")
        elif avg_time < 50:
            print("✅ Good performance (< 50ms)")
        elif avg_time < 100:
            print("⚠️ Acceptable performance (< 100ms)")
        else:
            print("❌ Poor performance (> 100ms)")
            
        return True
        
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False


def main():
    """Main test runner"""
    print("🚀 Starting Financial Rules Test Suite")
    print("=" * 60)
    
    success = True
    
    # Run main test suite
    if not run_financial_rules_tests():
        success = False
    
    # Run coverage analysis
    if not run_coverage_report():
        success = False
        
    # Run performance tests
    if not run_performance_tests():
        success = False
    
    # Final summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 All test suites completed successfully!")
        print("✅ Financial Rules system is ready for production!")
    else:
        print("💥 Some tests failed. Please review the output above.")
        
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
