"""
Test Models for Financial Rules

Unit tests for BaseFinancialRule, RuleCondition, RuleAction, and RuleExecutionLog models.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from company.models import Company
from ..models import BaseFinancialRule, RuleCondition, RuleAction, RuleExecutionLog


class BaseFinancialRuleModelTest(TestCase):
    """Test cases for BaseFinancialRule model"""
    
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
        
    def test_create_basic_rule(self):
        """Test creating a basic financial rule"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment',
            description='Test loan payment rule',
            priority=1,
            is_active=True
        )
        
        self.assertEqual(rule.name, 'Test Rule')
        self.assertEqual(rule.rule_type, 'loan_payment')
        self.assertTrue(rule.is_active)
        self.assertEqual(rule.usage_count, 0)
        self.assertIsNone(rule.last_used)
        
    def test_rule_string_representation(self):
        """Test the string representation of a rule"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment'
        )
        
        expected = 'Test Rule (loan_payment) - Test Company'
        self.assertEqual(str(rule), expected)
        
    def test_increment_usage(self):
        """Test incrementing rule usage statistics"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment'
        )
        
        # Initial state
        self.assertEqual(rule.usage_count, 0)
        self.assertIsNone(rule.last_used)
        
        # Increment usage
        rule.increment_usage()
        
        # Check updated state
        self.assertEqual(rule.usage_count, 1)
        self.assertIsNotNone(rule.last_used)
        
        # Increment again
        rule.increment_usage()
        self.assertEqual(rule.usage_count, 2)


class RuleConditionModelTest(TestCase):
    """Test cases for RuleCondition model"""
    
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
        
        self.rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment'
        )
        
    def test_create_condition(self):
        """Test creating a rule condition"""
        condition = RuleCondition.objects.create(
            rule=self.rule,
            field_name='customer_name',
            operator='equals',
            value='Rodriguez Rodriguez',
            sequence=1
        )
        
        self.assertEqual(condition.field_name, 'customer_name')
        self.assertEqual(condition.operator, 'equals')
        self.assertEqual(condition.value, 'Rodriguez Rodriguez')
        self.assertEqual(condition.sequence, 1)
        
    def test_condition_evaluate_equals(self):
        """Test equals operator evaluation"""
        condition = RuleCondition.objects.create(
            rule=self.rule,
            field_name='customer_name',
            operator='equals',
            value='Rodriguez Rodriguez',
            sequence=1
        )
        
        # Test exact match
        data = {'customer_name': 'Rodriguez Rodriguez'}
        self.assertTrue(condition.evaluate(data))
        
        # Test case insensitive match
        data = {'customer_name': 'rodriguez rodriguez'}
        self.assertTrue(condition.evaluate(data))
        
        # Test no match
        data = {'customer_name': 'John Smith'}
        self.assertFalse(condition.evaluate(data))
        
        # Test missing field
        data = {}
        self.assertFalse(condition.evaluate(data))
        
    def test_condition_evaluate_contains(self):
        """Test contains operator evaluation"""
        condition = RuleCondition.objects.create(
            rule=self.rule,
            field_name='customer_name',
            operator='contains',
            value='Rodriguez',
            sequence=1
        )
        
        # Test partial match
        data = {'customer_name': 'Rodriguez Rodriguez'}
        self.assertTrue(condition.evaluate(data))
        
        # Test case insensitive partial match
        data = {'customer_name': 'rodriguez smith'}
        self.assertTrue(condition.evaluate(data))
        
        # Test no match
        data = {'customer_name': 'John Smith'}
        self.assertFalse(condition.evaluate(data))
        
    def test_condition_evaluate_greater_than(self):
        """Test greater_than operator evaluation"""
        condition = RuleCondition.objects.create(
            rule=self.rule,
            field_name='transaction_amount',
            operator='greater_than',
            value='100.00',
            sequence=1
        )
        
        # Test greater than
        data = {'transaction_amount': Decimal('150.00')}
        self.assertTrue(condition.evaluate(data))
        
        # Test equal (should be false)
        data = {'transaction_amount': Decimal('100.00')}
        self.assertFalse(condition.evaluate(data))
        
        # Test less than
        data = {'transaction_amount': Decimal('50.00')}
        self.assertFalse(condition.evaluate(data))
        
    def test_condition_evaluate_regex(self):
        """Test regex operator evaluation"""
        condition = RuleCondition.objects.create(
            rule=self.rule,
            field_name='customer_name',
            operator='regex',
            value=r'^Rodriguez\s+\w+$',
            sequence=1
        )
        
        # Test regex match
        data = {'customer_name': 'Rodriguez Rodriguez'}
        self.assertTrue(condition.evaluate(data))
        
        # Test no match
        data = {'customer_name': 'John Rodriguez Smith'}
        self.assertFalse(condition.evaluate(data))


class RuleActionModelTest(TestCase):
    """Test cases for RuleAction model"""
    
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
        
        self.rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment'
        )
        
    def test_create_action(self):
        """Test creating a rule action"""
        action = RuleAction.objects.create(
            rule=self.rule,
            description_template='Interest Payment',
            account_code='4200',
            allocation_type='fixed',
            value=Decimal('35.42'),
            sequence=1
        )
        
        self.assertEqual(action.description_template, 'Interest Payment')
        self.assertEqual(action.account_code, '4200')
        self.assertEqual(action.allocation_type, 'fixed')
        self.assertEqual(action.value, Decimal('35.42'))
        
    def test_calculate_amount_fixed(self):
        """Test fixed amount calculation"""
        action = RuleAction.objects.create(
            rule=self.rule,
            description_template='Late Fee',
            account_code='4250',
            allocation_type='fixed',
            value=Decimal('25.00'),
            sequence=1
        )
        
        context = {'transaction_amount': Decimal('247.78')}
        amount = action.calculate_amount(Decimal('247.78'), context)
        
        self.assertEqual(amount, Decimal('25.00'))
        
    def test_calculate_amount_percentage(self):
        """Test percentage amount calculation"""
        action = RuleAction.objects.create(
            rule=self.rule,
            description_template='Interest Payment',
            account_code='4200',
            allocation_type='percentage',
            value=Decimal('14.30'),  # 14.3%
            sequence=1
        )
        
        context = {'transaction_amount': Decimal('247.78')}
        amount = action.calculate_amount(Decimal('247.78'), context)
        
        # 247.78 * 0.143 = 35.43254, rounded to 35.43
        expected = Decimal('35.43')
        self.assertEqual(amount, expected)
        
    def test_render_description(self):
        """Test description template rendering"""
        action = RuleAction.objects.create(
            rule=self.rule,
            description_template='Payment from {customer_name}',
            account_code='4200',
            allocation_type='fixed',
            value=Decimal('100.00'),
            sequence=1
        )
        
        context = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': Decimal('247.78')
        }
        
        description = action.render_description(context)
        self.assertEqual(description, 'Payment from Rodriguez Rodriguez')


class RuleExecutionLogModelTest(TestCase):
    """Test cases for RuleExecutionLog model"""
    
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
        
        self.rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment'
        )
        
    def test_create_execution_log(self):
        """Test creating an execution log"""
        log = RuleExecutionLog.objects.create(
            rule=self.rule,
            user=self.user,
            transaction_data={'customer_name': 'Rodriguez Rodriguez'},
            success=True,
            execution_time_ms=25,
            result_data=[{'account': '4200', 'amount': '35.42'}]
        )
        
        self.assertEqual(log.rule, self.rule)
        self.assertEqual(log.user, self.user)
        self.assertTrue(log.success)
        self.assertEqual(log.execution_time_ms, 25)
        self.assertIsNotNone(log.executed_at)
        
    def test_log_string_representation(self):
        """Test the string representation of an execution log"""
        log = RuleExecutionLog.objects.create(
            rule=self.rule,
            user=self.user,
            transaction_data={'customer_name': 'Rodriguez Rodriguez'},
            success=True
        )
        
        expected = f'Test Rule - {log.executed_at.strftime("%Y-%m-%d %H:%M")} - Success'
        self.assertEqual(str(log), expected)
