from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import datetime, timedelta

from company.models import Company
from loans_core.models import LoanProduct, Loan, LoanApplication
from loans_customers.models import Customer
from loans_payments.models import Payment
from .models import ReportConfiguration, ReportCache
from .services import ReportService


class LoanReportTestCase(TestCase):
    """
    Comprehensive test suite for the loan_report module
    """
    
    def setUp(self):
        """Set up test data"""
        # Create test user and company
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            address='123 Test St',
            email='test@company.com'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            company=self.company,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='555-0123'
        )
        
        # Create test loan product
        self.loan_product = LoanProduct.objects.create(
            company=self.company,
            name='Test Loan Product',
            interest_rate=Decimal('10.00'),
            min_amount=Decimal('1000.00'),
            max_amount=Decimal('50000.00')
        )
        
        # Create test loan application
        self.application = LoanApplication.objects.create(
            company=self.company,
            customer=self.customer,
            loan_product=self.loan_product,
            requested_amount=Decimal('10000.00'),
            status='approved'
        )
        
        # Create test loan
        self.loan = Loan.objects.create(
            company=self.company,
            customer=self.customer,
            loan_product=self.loan_product,
            application=self.application,
            principal_amount=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            term_months=12,
            status='active'
        )
        
        # Create test payment
        self.payment = Payment.objects.create(
            company=self.company,
            customer=self.customer,
            loan=self.loan,
            payment_amount=Decimal('500.00'),
            payment_date=datetime.now().date(),
            status='completed'
        )
        
        self.client = Client()
    
    def test_report_service_initialization(self):
        """Test ReportService can be initialized properly"""
        service = ReportService(self.company)
        self.assertEqual(service.company, self.company)
        self.assertTrue(service.use_cache)
    
    def test_portfolio_analytics(self):
        """Test portfolio analytics generation"""
        service = ReportService(self.company, use_cache=False)
        data = service.portfolio_analytics()
        
        # Verify basic structure
        self.assertIn('total_portfolio_value', data)
        self.assertIn('active_loans_count', data)
        self.assertIn('approval_rate', data)
        self.assertIn('collection_rate', data)
        
        # Verify data accuracy
        self.assertEqual(data['active_loans_count'], 1)
        self.assertEqual(data['total_portfolio_value'], Decimal('10000.00'))
    
    def test_fail_safe_operation(self):
        """Test that module fails gracefully without affecting main system"""
        # This test ensures that even if reports fail, the main system continues
        try:
            service = ReportService(self.company)
            # Force an error condition
            service.company = None
            data = service.portfolio_analytics()
            # Should not raise exception, just return safe data
            self.assertIsInstance(data, dict)
        except Exception as e:
            self.fail(f"Report module should not crash main system: {e}")
