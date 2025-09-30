"""
Smart Matching Engine Registry

Manages registration and execution of multiple smart matching engines.
Provides centralized access to all engines and their performance metrics.
"""

from typing import Dict, Any, List
from .base_engine import SmartMatchingEngine


class SmartMatchingRegistry:
    """Manages all smart matching engines"""
    
    def __init__(self):
        self.engines = {}
        self._register_default_engines()
    
    def register_engine(self, engine_class):
        """Register a new engine"""
        try:
            engine = engine_class()
            self.engines[engine.name] = engine
            print(f"✅ Registered smart matching engine: {engine.name}")
        except Exception as e:
            print(f"❌ Failed to register engine {engine_class.__name__}: {e}")
    
    def _register_default_engines(self):
        """Register all default engines"""
        try:
            from .engines.phone_priority_engine import PhonePriorityEngine
            self.register_engine(PhonePriorityEngine)
        except ImportError:
            print("📝 PhonePriorityEngine not yet implemented")
            
        try:
            from .engines.id_priority_engine import IDPriorityEngine
            self.register_engine(IDPriorityEngine)
        except ImportError:
            print("📝 IDPriorityEngine not yet implemented")
            
        try:
            from .engines.combined_signals_engine import CombinedSignalsEngine
            self.register_engine(CombinedSignalsEngine)
        except ImportError:
            print("📝 CombinedSignalsEngine not yet implemented")
    
    def run_all_engines(self, bank_description: str, amount: float) -> Dict[str, Any]:
        """Run all enabled engines and return results"""
        results = {}
        
        for engine_name, engine in self.engines.items():
            if engine.enabled:
                print(f"🔍 Running engine: {engine_name}")
                results[engine_name] = engine.safe_execute(bank_description, amount)
                
        return results
    
    def get_best_suggestions(self, bank_description: str, amount: float, max_results: int = 5) -> List[Dict]:
        """Get best loan suggestions from all engines combined"""
        engine_results = self.run_all_engines(bank_description, amount)
        
        # Compile all suggestions
        all_suggestions = []
        for engine_name, result in engine_results.items():
            if result['success']:
                for suggestion in result['suggestions']:
                    suggestion['suggested_by'] = engine_name
                    all_suggestions.append(suggestion)
        
        # Remove duplicates (same loan_id)
        unique_suggestions = {}
        for suggestion in all_suggestions:
            loan_id = suggestion.get('loan_id')
            if loan_id:
                if loan_id not in unique_suggestions or suggestion['confidence'] > unique_suggestions[loan_id]['confidence']:
                    unique_suggestions[loan_id] = suggestion
        
        # Sort by confidence and return top results
        best_suggestions = sorted(unique_suggestions.values(), key=lambda x: x['confidence'], reverse=True)
        return best_suggestions[:max_results]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics for all engines"""
        report = {
            'engines': {},
            'summary': {
                'total_engines': len(self.engines),
                'enabled_engines': sum(1 for engine in self.engines.values() if engine.enabled),
                'disabled_engines': sum(1 for engine in self.engines.values() if not engine.enabled)
            }
        }
        
        for engine_name, engine in self.engines.items():
            report['engines'][engine_name] = {
                'enabled': engine.enabled,
                'success_rate': engine.get_success_rate(),
                'metrics': engine.performance_metrics
            }
        
        return report
    
    def enable_engine(self, engine_name: str):
        """Enable a specific engine"""
        if engine_name in self.engines:
            self.engines[engine_name].enable()
            print(f"✅ Enabled engine: {engine_name}")
        else:
            print(f"❌ Engine not found: {engine_name}")
    
    def disable_engine(self, engine_name: str):
        """Disable a specific engine"""
        if engine_name in self.engines:
            self.engines[engine_name].disable()
            print(f"🔇 Disabled engine: {engine_name}")
        else:
            print(f"❌ Engine not found: {engine_name}")


# Global registry instance
_registry = None

def get_registry() -> SmartMatchingRegistry:
    """Get global registry instance (singleton pattern)"""
    global _registry
    if _registry is None:
        _registry = SmartMatchingRegistry()
    return _registry
