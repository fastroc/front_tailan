"""
Base Engine for Smart Matching System

Provides abstract base class and fail-safe execution wrapper for all smart matching engines.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import traceback


class SmartMatchingEngine(ABC):
    """Base class for all smart matching engines"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.version = "1.0"
        self.enabled = True
        self.performance_metrics = {
            'total_runs': 0,
            'successful_runs': 0,
            'avg_processing_time': 0,
            'confidence_accuracy': 0,
            'last_error': None
        }
    
    @abstractmethod
    def detect_loans(self, bank_description: str, amount: float) -> List[Dict]:
        """
        Detect loan applications from bank transaction description
        
        Args:
            bank_description: Bank transaction description text
            amount: Transaction amount
        
        Returns:
            List of dictionaries containing:
            {
                'loan_id': 123,
                'loan_number': 'L2025001', 
                'customer_name': 'John Smith',
                'confidence': 95,
                'method': 'phone_match',
                'matched_data': '99123456',
                'loan_amount': 50000.00,
                'loan_type': 'auto'
            }
        """
        pass
    
    def safe_execute(self, bank_description: str, amount: float) -> Dict[str, Any]:
        """Safe execution wrapper with error handling and metrics"""
        start_time = time.time()
        result = {
            'engine': self.name,
            'success': False,
            'suggestions': [],
            'processing_time': 0,
            'error': None
        }
        
        try:
            if not self.enabled:
                result['error'] = 'Engine disabled'
                return result
                
            suggestions = self.detect_loans(bank_description, amount)
            result['suggestions'] = suggestions or []
            result['success'] = True
            
            # Update metrics
            self.performance_metrics['successful_runs'] += 1
            
        except Exception as e:
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
            self.performance_metrics['last_error'] = str(e)
            
        finally:
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time
            self.performance_metrics['total_runs'] += 1
            
            # Update average processing time
            if self.performance_metrics['total_runs'] > 0:
                total_time = (self.performance_metrics['avg_processing_time'] * 
                             (self.performance_metrics['total_runs'] - 1) + processing_time)
                self.performance_metrics['avg_processing_time'] = total_time / self.performance_metrics['total_runs']
        
        return result
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.performance_metrics['total_runs'] == 0:
            return 0.0
        return (self.performance_metrics['successful_runs'] / self.performance_metrics['total_runs']) * 100
    
    def disable(self):
        """Disable this engine"""
        self.enabled = False
    
    def enable(self):
        """Enable this engine"""
        self.enabled = True
