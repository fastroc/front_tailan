"""
Bank Rules Module
-----------------
Modular rule-based transaction matching system.

Feature Flag: BANK_RULES_ENABLED
Can be disabled without breaking reconciliation system.
"""

# Feature flag - can be toggled to disable entire module
BANK_RULES_ENABLED = True


def get_rules_enabled():
    """Check if bank rules feature is enabled"""
    return BANK_RULES_ENABLED


def get_rule_suggestions(transaction, company):
    """
    Safe wrapper to get rule suggestions.
    Returns empty list if feature is disabled or on error.
    
    Args:
        transaction: BankTransaction dict with fields
        company: Company instance
        
    Returns:
        list: Rule suggestions in smart suggestion format
    """
    if not get_rules_enabled():
        return []
    
    try:
        from .services import RuleEngineService
        return RuleEngineService.get_suggestions_from_rules(transaction, company)
    except Exception as e:
        # Fail gracefully - don't break reconciliation if rules break
        print(f"⚠️ Bank Rules Error: {e}")
        return []


# Export public API
__all__ = [
    'get_rules_enabled',
    'get_rule_suggestions',
    'BANK_RULES_ENABLED',
]