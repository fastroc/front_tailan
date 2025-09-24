"""
Test Base Rule Engine

Unit tests for the base rule engine functionality including condition evaluation,
action execution, and result handling.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from company.models import Company
from ..models import BaseFinancialRule, RuleCondition, RuleAction
from ..engines.base_engine import BaseRuleEngine, RuleEngineFactory, RuleEngineResult


class RuleEngineResultTest(TestCase):
    """Test cases for RuleEngineResult class"""
    
    def test_create_successful_result(self):
        """Test creating a successful result"""
        split_lines = [
            {'description': 'Interest', 'account_code': '4200', 'amount': '35.42'},
            {'description': 'Principal', 'account_code': '1200', 'amount': '212.36'}
        ]
        
        result = RuleEngineResult(
            success=True,
            split_lines=split_lines,
            matched_rules=[]
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.split_lines), 2)
        self.assertEqual(result.total_allocated, Decimal('247.78'))
        
    def test_create_failed_result(self):
        """Test creating a failed result"""
        result = RuleEngineResult(
            success=False,
            error_message='No matching rules found'
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, 'No matching rules found')
        self.assertEqual(result.total_allocated, Decimal('0'))
        
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = RuleEngineResult(
            success=True,
            split_lines=[{'account_code': '4200', 'amount': '35.42'}],
            matched_rules=[]
        )
        
        result_dict = result.to_dict()
        
        self.assertIn('success', result_dict)
        self.assertIn('split_lines', result_dict)
        self.assertIn('total_allocated', result_dict)
        self.assertTrue(result_dict['success'])


class BaseRuleEngineTest(TestCase):
    """Test cases for BaseRuleEngine class"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.user
        )
        
        self.engine = BaseRuleEngine(self.company.id)
        
    def test_engine_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.company_id, self.company.id)
        self.assertFalse(self.engine.debug_mode)
        
    def test_enable_debug(self):
        """Test enabling debug mode"""
        self.engine.enable_debug()
        self.assertTrue(self.engine.debug_mode)
        
    def test_evaluate_transaction_no_rules(self):
        """Test transaction evaluation with no rules"""
        transaction_data = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': Decimal('247.78')
        }
        
        result = self.engine.evaluate_transaction(transaction_data)
        
        self.assertFalse(result.success)
        self.assertIn('No matching rules found', result.error_message)
        
    def test_evaluate_transaction_with_matching_rule(self):
        """Test transaction evaluation with a matching rule"""
        # Create a rule that matches all transactions
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Universal Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        # Add an action
        RuleAction.objects.create(
            rule=rule,
            description_template='Interest Payment',
            account_code='4200',
            allocation_type='fixed',
            value=Decimal('35.42'),
            sequence=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Principal Payment',
            account_code='1200',
            allocation_type='remainder',
            value=Decimal('0'),
            sequence=2
        )
        
        transaction_data = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': Decimal('247.78')
        }
        
        result = self.engine.evaluate_transaction(transaction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.matched_rules), 1)
        self.assertEqual(len(result.split_lines), 2)
        self.assertEqual(result.total_allocated, Decimal('247.78'))
        
    def test_evaluate_transaction_with_conditions(self):
        """Test transaction evaluation with conditions"""
        # Create a rule with conditions
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Rodriguez Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        # Add condition for Rodriguez
        RuleCondition.objects.create(
            rule=rule,
            field_name='customer_name',
            operator='contains',
            value='Rodriguez',
            sequence=1
        )
        
        # Add action
        RuleAction.objects.create(
            rule=rule,
            description_template='Rodriguez Payment',
            account_code='4200',
            allocation_type='percentage',
            value=Decimal('100'),
            sequence=1
        )
        
        # Test matching transaction
        transaction_data = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': Decimal('100.00')
        }
        
        result = self.engine.evaluate_transaction(transaction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.matched_rules), 1)
        
        # Test non-matching transaction
        transaction_data = {
            'customer_name': 'John Smith',
            'transaction_amount': Decimal('100.00')
        }
        
        result = self.engine.evaluate_transaction(transaction_data)
        
        self.assertFalse(result.success)
        
    def test_rule_priority_ordering(self):
        """Test that rules are evaluated in priority order"""
        # Create high priority rule
        high_priority_rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='High Priority Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1,
            stop_on_match=True
        )
        
        # Create low priority rule
        low_priority_rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Low Priority Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=5,
            stop_on_match=True
        )
        
        # Add actions to both rules
        for rule in [high_priority_rule, low_priority_rule]:
            RuleAction.objects.create(
                rule=rule,
                description_template=f'{rule.name} Action',
                account_code='4200',
                allocation_type='fixed',
                value=Decimal('50.00'),
                sequence=1
            )
        
        transaction_data = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': Decimal('100.00')
        }
        
        result = self.engine.evaluate_transaction(transaction_data)
        
        # Should match only the high priority rule due to stop_on_match
        self.assertTrue(result.success)
        self.assertEqual(len(result.matched_rules), 1)
        self.assertEqual(result.matched_rules[0].name, 'High Priority Rule')


class RuleEngineFactoryTest(TestCase):
    """Test cases for RuleEngineFactory"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.user
        )
        
    def test_create_base_engine(self):
        """Test creating a base engine"""
        engine = RuleEngineFactory.create_engine(self.company.id)
        
        self.assertIsInstance(engine, BaseRuleEngine)
        self.assertEqual(engine.company_id, self.company.id)
        
    def test_create_loan_engine(self):
        """Test creating a loan payment engine"""
        engine = RuleEngineFactory.create_engine(self.company.id, ['loan_payment'])
        
        # Should be a LoanPaymentEngine (subclass of BaseRuleEngine)
        self.assertIsInstance(engine, BaseRuleEngine)
        self.assertEqual(engine.company_id, self.company.id)
        
    def test_create_contact_engine(self):
        """Test creating a contact engine"""
        engine = RuleEngineFactory.create_engine(self.company.id, ['contact_based'])
        
        # Should be a ContactRuleEngine (subclass of BaseRuleEngine)
        self.assertIsInstance(engine, BaseRuleEngine)
        self.assertEqual(engine.company_id, self.company.id)


class RuleValidationTest(TestCase):
    """Test cases for rule validation and edge cases"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.user
        )
        
        self.engine = BaseRuleEngine(self.company.id)
        
    def test_rounding_adjustment(self):
        """Test rounding adjustment for small differences"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Rounding Test Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        # Create actions that don't add up exactly due to rounding
        RuleAction.objects.create(
            rule=rule,
            description_template='Action 1',
            account_code='4200',
            allocation_type='percentage',
            value=Decimal('33.33'),  # 33.33% of 100 = 33.33
            sequence=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Action 2',
            account_code='4201',
            allocation_type='percentage',
            value=Decimal('33.33'),  # 33.33% of 100 = 33.33
            sequence=2
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Action 3',
            account_code='4202',
            allocation_type='percentage',
            value=Decimal('33.34'),  # 33.34% of 100 = 33.34
            sequence=3
        )
        
        transaction_data = {
            'customer_name': 'Test Customer',
            'transaction_amount': Decimal('100.00')
        }
        
        result = self.engine.evaluate_transaction(transaction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(result.total_allocated, Decimal('100.00'))
        
    def test_inactive_rule_ignored(self):
        """Test that inactive rules are ignored"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Inactive Rule',
            rule_type='loan_payment',
            is_active=False,  # Inactive
            priority=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Should not execute',
            account_code='4200',
            allocation_type='fixed',
            value=Decimal('100.00'),
            sequence=1
        )
        
        transaction_data = {
            'customer_name': 'Test Customer',
            'transaction_amount': Decimal('100.00')
        }
        
        result = self.engine.evaluate_transaction(transaction_data)
        
        # Should fail because the only rule is inactive
        self.assertFalse(result.success)
        
    def test_empty_transaction_data(self):
        """Test handling of empty transaction data"""
        result = self.engine.evaluate_transaction({})
        
        # Should handle gracefully without crashing
        self.assertIsInstance(result, RuleEngineResult)
