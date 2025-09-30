"""
Smart Matching System for Bank Reconciliation

Modular architecture for intelligent loan customer detection from bank transaction descriptions.
Supports multiple competing engines with performance comparison and learning capabilities.
"""

from .registry import SmartMatchingRegistry
from .base_engine import SmartMatchingEngine

__all__ = ['SmartMatchingRegistry', 'SmartMatchingEngine']
