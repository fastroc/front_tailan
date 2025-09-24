"""
Test API Views

Unit tests for the financial rules API endpoints including rule evaluation,
testing, and management views.
"""

import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from company.models import Company
from ..models import BaseFinancialRule, RuleCondition, RuleAction


class APIViewsTest(TestCase):
    """Test cases for API views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.user
        )
        
        # Login user
        self.client.login(username='testuser', password='testpass123')
        
        # Set active company in session
        session = self.client.session
        session['active_company_id'] = self.company.id
        session.save()
        
    def test_evaluate_rules_no_rules(self):
        """Test rule evaluation with no rules configured"""
        url = reverse('financial_rules:evaluate_rules')
        
        data = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': '247.78',
            'transaction_description': 'Loan payment'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(len(response_data['split_data']), 0)
        
    def test_evaluate_rules_with_matching_rule(self):
        """Test rule evaluation with a matching rule"""
        # Create a test rule
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        # Add condition
        RuleCondition.objects.create(
            rule=rule,
            field_name='customer_name',
            operator='contains',
            value='Rodriguez',
            sequence=1
        )
        
        # Add actions
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
        
        url = reverse('financial_rules:evaluate_rules')
        
        data = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': '247.78',
            'transaction_description': 'Loan payment'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['split_data']), 2)
        self.assertEqual(response_data['total_allocated'], '247.78')
        self.assertEqual(response_data['rules_matched'], 1)
        
    def test_evaluate_rules_json_input(self):
        """Test rule evaluation with JSON input"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Payment',
            account_code='4200',
            allocation_type='percentage',
            value=Decimal('100'),
            sequence=1
        )
        
        url = reverse('financial_rules:evaluate_rules')
        
        data = {
            'customer_name': 'Test Customer',
            'transaction_amount': 100.00,
            'transaction_description': 'Test payment'
        }
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
    def test_evaluate_rules_invalid_data(self):
        """Test rule evaluation with invalid data"""
        url = reverse('financial_rules:evaluate_rules')
        
        # Missing required fields
        data = {
            'customer_name': 'Test Customer'
            # Missing transaction_amount
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_type'], 'validation_error')
        
    def test_test_rule_endpoint(self):
        """Test the test rule endpoint"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Test Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Test Payment',
            account_code='4200',
            allocation_type='fixed',
            value=Decimal('50.00'),
            sequence=1
        )
        
        url = reverse('financial_rules:test_rule', kwargs={'rule_id': rule.id})
        
        test_data = {
            'customer_name': 'Test Customer',
            'transaction_amount': '100.00',
            'transaction_description': 'Test payment'
        }
        
        response = self.client.post(
            url,
            {'test_data': json.dumps(test_data)}
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['rule_matched'])
        self.assertEqual(len(response_data['split_data']), 1)
        
    def test_test_rule_not_found(self):
        """Test testing a non-existent rule"""
        url = reverse('financial_rules:test_rule', kwargs={'rule_id': 99999})
        
        test_data = {
            'customer_name': 'Test Customer',
            'transaction_amount': '100.00'
        }
        
        response = self.client.post(
            url,
            {'test_data': json.dumps(test_data)}
        )
        
        self.assertEqual(response.status_code, 404)
        
    def test_get_available_rules(self):
        """Test getting available rules"""
        # Create some test rules
        rule1 = BaseFinancialRule.objects.create(
            company=self.company,
            name='Rule 1',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        rule2 = BaseFinancialRule.objects.create(
            company=self.company,
            name='Rule 2',
            rule_type='contact_based',
            is_active=False,
            priority=2
        )
        
        url = reverse('financial_rules:get_available_rules')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['total_rules'], 2)
        self.assertEqual(len(response_data['rules']), 2)
        
        # Check rule data structure
        rule_data = response_data['rules'][0]
        self.assertIn('id', rule_data)
        self.assertIn('name', rule_data)
        self.assertIn('rule_type', rule_data)
        self.assertIn('is_active', rule_data)
        self.assertIn('priority', rule_data)
        
    def test_auto_split_transaction_legacy(self):
        """Test the legacy auto-split endpoint"""
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Legacy Rule',
            rule_type='loan_payment',
            is_active=True,
            priority=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Interest',
            account_code='4200',
            allocation_type='fixed',
            value=Decimal('35.42'),
            sequence=1
        )
        
        RuleAction.objects.create(
            rule=rule,
            description_template='Principal',
            account_code='1200',
            allocation_type='remainder',
            value=Decimal('0'),
            sequence=2
        )
        
        url = reverse('financial_rules:auto_split_transaction')
        
        data = {
            'customer_name': 'Rodriguez Rodriguez',
            'amount': '247.78',
            'description': 'Loan payment'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['split_lines']), 2)
        self.assertEqual(response_data['total_amount'], 247.78)
        
        # Check legacy format
        split_line = response_data['split_lines'][0]
        self.assertIn('description', split_line)
        self.assertIn('account', split_line)
        self.assertIn('amount', split_line)
        
    def test_unauthorized_access(self):
        """Test unauthorized access to API endpoints"""
        # Logout user
        self.client.logout()
        
        url = reverse('financial_rules:evaluate_rules')
        data = {'customer_name': 'Test', 'transaction_amount': '100'}
        
        response = self.client.post(url, data)
        
        # Should redirect to login or return 403
        self.assertIn(response.status_code, [302, 403])
        
    def test_no_company_session(self):
        """Test API access without company in session"""
        # Clear company from session
        session = self.client.session
        if 'active_company_id' in session:
            del session['active_company_id']
        session.save()
        
        url = reverse('financial_rules:evaluate_rules')
        data = {'customer_name': 'Test', 'transaction_amount': '100'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error_type'], 'company_error')


class IntegrationTest(TestCase):
    """Integration tests for the complete workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        session = self.client.session
        session['active_company_id'] = self.company.id
        session.save()
        
    def test_complete_loan_payment_workflow(self):
        """Test a complete loan payment rule workflow"""
        # Step 1: Create a loan payment rule
        rule = BaseFinancialRule.objects.create(
            company=self.company,
            name='Rodriguez Loan Payment',
            rule_type='loan_payment',
            description='Auto-split Rodriguez loan payments',
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
        
        # Add late fee action
        RuleAction.objects.create(
            rule=rule,
            description_template='Late Fee Payment',
            account_code='4250',
            allocation_type='fixed',
            value=Decimal('0.00'),
            sequence=1
        )
        
        # Add interest action
        RuleAction.objects.create(
            rule=rule,
            description_template='Interest Payment',
            account_code='4200',
            allocation_type='percentage',
            value=Decimal('14.30'),
            sequence=2
        )
        
        # Add principal action (remainder)
        RuleAction.objects.create(
            rule=rule,
            description_template='Principal Payment',
            account_code='1200',
            allocation_type='remainder',
            value=Decimal('0'),
            sequence=3
        )
        
        # Step 2: Test the rule
        test_url = reverse('financial_rules:test_rule', kwargs={'rule_id': rule.id})
        
        test_data = {
            'customer_name': 'Rodriguez Rodriguez',
            'transaction_amount': '247.78',
            'transaction_description': 'Loan payment'
        }
        
        test_response = self.client.post(
            test_url,
            {'test_data': json.dumps(test_data)}
        )
        
        self.assertEqual(test_response.status_code, 200)
        
        test_result = json.loads(test_response.content)
        self.assertTrue(test_result['success'])
        self.assertTrue(test_result['rule_matched'])
        self.assertEqual(len(test_result['split_data']), 3)
        
        # Step 3: Evaluate actual transaction
        eval_url = reverse('financial_rules:evaluate_rules')
        
        eval_response = self.client.post(eval_url, test_data)
        
        self.assertEqual(eval_response.status_code, 200)
        
        eval_result = json.loads(eval_response.content)
        self.assertTrue(eval_result['success'])
        self.assertEqual(eval_result['rules_matched'], 1)
        self.assertEqual(eval_result['total_allocated'], '247.78')
        
        # Verify the allocation breakdown
        split_data = eval_result['split_data']
        
        # Late fee: $0.00
        late_fee = next(line for line in split_data if line['account_code'] == '4250')
        self.assertEqual(late_fee['amount'], '0.00')
        
        # Interest: 14.3% of $247.78 = $35.43
        interest = next(line for line in split_data if line['account_code'] == '4200')
        self.assertEqual(interest['amount'], '35.43')
        
        # Principal: remainder = $247.78 - $35.43 = $212.35
        principal = next(line for line in split_data if line['account_code'] == '1200')
        self.assertEqual(principal['amount'], '212.35')
        
        # Step 4: Verify rule usage was tracked
        rule.refresh_from_db()
        self.assertGreater(rule.usage_count, 0)
        self.assertIsNotNone(rule.last_used)
