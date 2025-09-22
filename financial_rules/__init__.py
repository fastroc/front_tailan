"""
Financial Rules Module

This module provides a flexible rule engine for automatic transaction splitting
based on various conditions like customer patterns, amount ranges, and transaction types.

Key Features:
- Rule-based transaction splitting
- Support for loan payments, contact-based rules, and custom allocations
- Priority-based rule matching
- Extensible condition and action system
"""

default_app_config = 'financial_rules.apps.FinancialRulesConfig'
