"""
Confidence Calculation System

Centralized system for calculating and managing confidence scores across all smart matching engines.
Provides weighted scoring, ensemble methods, and confidence calibration.
"""

from typing import Dict, List, Optional, Any
from collections import defaultdict
import statistics
from datetime import datetime


class ConfidenceCalculator:
    """Centralized confidence calculation and management system"""
    
    def __init__(self):
        self.engine_weights = {
            'Phone Priority Engine': 0.85,
            'ID Priority Engine': 0.90,
            'Combined Signals Engine': 0.95,
            'License Plate Engine': 0.80,
            'Loan Disbursement Engine': 0.88,
            'Recurring Pattern Engine': 0.75
        }
        
        self.confidence_history = defaultdict(list)
        self.feedback_data = defaultdict(list)  # User feedback for calibration
        
    def calculate_weighted_confidence(self, suggestions: List[Dict]) -> List[Dict]:
        """Calculate weighted confidence scores for multiple engine suggestions"""
        weighted_suggestions = []
        
        for suggestion in suggestions:
            engine_name = suggestion.get('engine', 'Unknown Engine')
            original_confidence = suggestion.get('confidence', 50)
            engine_weight = self.engine_weights.get(engine_name, 0.5)
            
            # Apply engine-specific weighting
            weighted_confidence = original_confidence * engine_weight
            
            # Apply method-specific adjustments
            method_bonus = self._get_method_confidence_bonus(suggestion.get('method', ''))
            weighted_confidence += method_bonus
            
            # Apply data quality adjustments
            data_quality_factor = self._assess_data_quality(suggestion)
            weighted_confidence *= data_quality_factor
            
            # Ensure confidence stays within bounds
            final_confidence = max(1, min(99, round(weighted_confidence)))
            
            # Update suggestion with calculated confidence
            updated_suggestion = suggestion.copy()
            updated_suggestion['confidence'] = final_confidence
            updated_suggestion['original_confidence'] = original_confidence
            updated_suggestion['engine_weight'] = engine_weight
            updated_suggestion['method_bonus'] = method_bonus
            updated_suggestion['data_quality_factor'] = data_quality_factor
            
            weighted_suggestions.append(updated_suggestion)
            
            # Track confidence history
            self._track_confidence_history(engine_name, final_confidence)
        
        return weighted_suggestions
    
    def _get_method_confidence_bonus(self, method: str) -> float:
        """Get confidence bonus based on matching method"""
        method_bonuses = {
            'exact_phone_match': 10,
            'exact_id_match': 12,
            'combined_signals': 8,
            'license_plate_exact': 5,
            'loan_disbursement_pattern': 7,
            'recurring_pattern_exact': 8,
            'recurring_pattern_partial': 3,
            'partial_phone_match': 2,
            'partial_id_match': 4,
            'name_similarity': 1,
            'amount_similarity': 2
        }
        
        return method_bonuses.get(method, 0)
    
    def _assess_data_quality(self, suggestion: Dict) -> float:
        """Assess data quality and return confidence multiplier"""
        quality_score = 1.0
        
        # Check for required fields
        required_fields = ['customer_name', 'matched_data']
        for field in required_fields:
            if not suggestion.get(field):
                quality_score -= 0.1
        
        # Check loan information completeness
        if suggestion.get('loan_amount', 0) > 0:
            quality_score += 0.05
        
        if suggestion.get('loan_number') and suggestion.get('loan_number') != 'N/A':
            quality_score += 0.05
        
        if suggestion.get('customer_id'):
            quality_score += 0.05
        
        # Check method specificity
        method = suggestion.get('method', '')
        if 'exact' in method:
            quality_score += 0.1
        elif 'partial' in method:
            quality_score += 0.05
        
        # Ensure quality score stays reasonable
        return max(0.7, min(1.3, quality_score))
    
    def calculate_ensemble_confidence(self, suggestions_by_engine: Dict[str, List[Dict]]) -> Dict:
        """Calculate ensemble confidence from multiple engines"""
        if not suggestions_by_engine:
            return {'confidence': 0, 'consensus': False, 'participating_engines': []}
        
        all_suggestions = []
        engine_contributions = {}
        
        # Collect all suggestions with weights
        for engine_name, suggestions in suggestions_by_engine.items():
            weighted_suggestions = self.calculate_weighted_confidence(suggestions)
            all_suggestions.extend(weighted_suggestions)
            
            if weighted_suggestions:
                # Get best suggestion from this engine
                best_suggestion = max(weighted_suggestions, key=lambda x: x['confidence'])
                engine_contributions[engine_name] = best_suggestion['confidence']
        
        if not all_suggestions:
            return {'confidence': 0, 'consensus': False, 'participating_engines': []}
        
        # Calculate ensemble metrics
        confidences = [s['confidence'] for s in all_suggestions]
        
        ensemble_result = {
            'confidence': round(statistics.mean(confidences)),
            'max_confidence': max(confidences),
            'min_confidence': min(confidences),
            'confidence_std': round(statistics.stdev(confidences)) if len(confidences) > 1 else 0,
            'consensus': self._check_consensus(confidences),
            'participating_engines': list(suggestions_by_engine.keys()),
            'total_suggestions': len(all_suggestions),
            'engine_contributions': engine_contributions,
            'best_suggestion': max(all_suggestions, key=lambda x: x['confidence'])
        }
        
        return ensemble_result
    
    def _check_consensus(self, confidences: List[float]) -> bool:
        """Check if engines have consensus (low variance in confidence)"""
        if len(confidences) < 2:
            return True
        
        std_dev = statistics.stdev(confidences)
        mean_confidence = statistics.mean(confidences)
        
        # Consensus if standard deviation is less than 15% of mean
        consensus_threshold = mean_confidence * 0.15
        return std_dev <= consensus_threshold
    
    def calibrate_confidence(self, suggestion: Dict, actual_outcome: bool) -> Dict:
        """Calibrate confidence based on actual outcomes (user feedback)"""
        engine_name = suggestion.get('engine', 'Unknown')
        predicted_confidence = suggestion.get('confidence', 50)
        method = suggestion.get('method', '')
        
        # Record feedback
        feedback_entry = {
            'engine': engine_name,
            'method': method,
            'predicted_confidence': predicted_confidence,
            'actual_outcome': actual_outcome,
            'timestamp': datetime.now()
        }
        
        self.feedback_data[engine_name].append(feedback_entry)
        
        # Calculate calibration adjustment
        calibration_adjustment = self._calculate_calibration_adjustment(engine_name, method)
        
        return {
            'original_confidence': predicted_confidence,
            'calibration_adjustment': calibration_adjustment,
            'calibrated_confidence': max(1, min(99, predicted_confidence + calibration_adjustment)),
            'feedback_recorded': True
        }
    
    def _calculate_calibration_adjustment(self, engine_name: str, method: str) -> float:
        """Calculate confidence adjustment based on historical feedback"""
        if engine_name not in self.feedback_data:
            return 0
        
        feedback_entries = self.feedback_data[engine_name]
        if len(feedback_entries) < 5:  # Need minimum samples
            return 0
        
        # Get feedback for specific method or all methods
        relevant_feedback = [
            f for f in feedback_entries 
            if f['method'] == method or method == ''
        ]
        
        if len(relevant_feedback) < 3:
            relevant_feedback = feedback_entries  # Fall back to all feedback
        
        # Calculate accuracy vs predicted confidence
        correct_predictions = sum(1 for f in relevant_feedback if f['actual_outcome'])
        total_predictions = len(relevant_feedback)
        actual_accuracy = correct_predictions / total_predictions
        
        # Average predicted confidence
        avg_predicted_confidence = statistics.mean(
            f['predicted_confidence'] for f in relevant_feedback
        )
        
        # Calculate adjustment (convert percentage to confidence points)
        predicted_accuracy = avg_predicted_confidence / 100
        accuracy_difference = actual_accuracy - predicted_accuracy
        
        # Convert to confidence point adjustment
        adjustment = accuracy_difference * 20  # Scale factor
        
        return round(adjustment, 1)
    
    def get_engine_performance_stats(self) -> Dict:
        """Get performance statistics for all engines"""
        stats = {}
        
        for engine_name, feedback_entries in self.feedback_data.items():
            if not feedback_entries:
                continue
            
            correct_predictions = sum(1 for f in feedback_entries if f['actual_outcome'])
            total_predictions = len(feedback_entries)
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
            
            avg_confidence = statistics.mean(f['predicted_confidence'] for f in feedback_entries)
            
            stats[engine_name] = {
                'total_predictions': total_predictions,
                'correct_predictions': correct_predictions,
                'accuracy': round(accuracy * 100, 1),
                'average_confidence': round(avg_confidence, 1),
                'weight': self.engine_weights.get(engine_name, 0.5),
                'last_calibration': max(f['timestamp'] for f in feedback_entries) if feedback_entries else None
            }
        
        return stats
    
    def suggest_weight_adjustments(self) -> Dict:
        """Suggest engine weight adjustments based on performance"""
        stats = self.get_engine_performance_stats()
        suggestions = {}
        
        for engine_name, engine_stats in stats.items():
            if engine_stats['total_predictions'] < 10:
                continue  # Need more data
            
            current_weight = self.engine_weights.get(engine_name, 0.5)
            accuracy = engine_stats['accuracy'] / 100
            
            # Suggest weight based on accuracy
            if accuracy >= 0.9:
                suggested_weight = min(0.95, current_weight + 0.05)
            elif accuracy >= 0.8:
                suggested_weight = current_weight  # Keep current
            elif accuracy >= 0.7:
                suggested_weight = max(0.3, current_weight - 0.05)
            else:
                suggested_weight = max(0.2, current_weight - 0.1)
            
            if abs(suggested_weight - current_weight) > 0.01:
                suggestions[engine_name] = {
                    'current_weight': current_weight,
                    'suggested_weight': round(suggested_weight, 2),
                    'reason': f"Based on {accuracy:.1%} accuracy over {engine_stats['total_predictions']} predictions"
                }
        
        return suggestions
    
    def apply_weight_adjustments(self, adjustments: Dict):
        """Apply suggested weight adjustments"""
        for engine_name, adjustment in adjustments.items():
            if engine_name in self.engine_weights:
                old_weight = self.engine_weights[engine_name]
                new_weight = adjustment['suggested_weight']
                self.engine_weights[engine_name] = new_weight
                
                print(f"Updated {engine_name} weight: {old_weight:.2f} → {new_weight:.2f}")
    
    def _track_confidence_history(self, engine_name: str, confidence: float):
        """Track confidence scores for trend analysis"""
        self.confidence_history[engine_name].append({
            'confidence': confidence,
            'timestamp': datetime.now()
        })
        
        # Keep only recent history (last 1000 entries)
        if len(self.confidence_history[engine_name]) > 1000:
            self.confidence_history[engine_name] = self.confidence_history[engine_name][-1000:]
    
    def get_confidence_trends(self, engine_name: Optional[str] = None) -> Dict:
        """Get confidence trends for engines"""
        if engine_name:
            if engine_name not in self.confidence_history:
                return {}
            
            history = self.confidence_history[engine_name]
            confidences = [entry['confidence'] for entry in history]
            
            return {
                'engine': engine_name,
                'total_calculations': len(confidences),
                'average_confidence': round(statistics.mean(confidences), 1) if confidences else 0,
                'confidence_trend': self._calculate_trend(confidences),
                'last_10_average': round(statistics.mean(confidences[-10:]), 1) if len(confidences) >= 10 else None
            }
        else:
            # Return trends for all engines
            trends = {}
            for engine in self.confidence_history.keys():
                trends[engine] = self.get_confidence_trends(engine)
            return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 10:
            return 'insufficient_data'
        
        recent = values[-10:]
        older = values[-20:-10] if len(values) >= 20 else values[:-10]
        
        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)
        
        diff = recent_avg - older_avg
        
        if diff > 2:
            return 'improving'
        elif diff < -2:
            return 'declining'
        else:
            return 'stable'
    
    def export_calibration_data(self) -> Dict:
        """Export calibration data for backup or analysis"""
        return {
            'engine_weights': self.engine_weights.copy(),
            'feedback_data': {
                engine: [
                    {
                        'engine': f['engine'],
                        'method': f['method'],
                        'predicted_confidence': f['predicted_confidence'],
                        'actual_outcome': f['actual_outcome'],
                        'timestamp': f['timestamp'].isoformat()
                    } for f in feedback_list
                ] for engine, feedback_list in self.feedback_data.items()
            },
            'export_timestamp': datetime.now().isoformat(),
            'total_feedback_entries': sum(len(feedback) for feedback in self.feedback_data.values())
        }
    
    def import_calibration_data(self, data: Dict):
        """Import calibration data from external source"""
        if 'engine_weights' in data:
            self.engine_weights.update(data['engine_weights'])
        
        if 'feedback_data' in data:
            for engine, feedback_list in data['feedback_data'].items():
                for feedback in feedback_list:
                    feedback_entry = feedback.copy()
                    feedback_entry['timestamp'] = datetime.fromisoformat(feedback['timestamp'])
                    self.feedback_data[engine].append(feedback_entry)
        
        print(f"Imported calibration data for {len(data.get('feedback_data', {}))} engines")
    
    def get_system_info(self) -> Dict:
        """Get confidence calculation system information"""
        return {
            'name': 'Confidence Calculation System',
            'version': '1.0.0',
            'description': 'Centralized confidence calculation and management',
            'supported_engines': list(self.engine_weights.keys()),
            'total_feedback_entries': sum(len(feedback) for feedback in self.feedback_data.values()),
            'calibration_enabled': True,
            'ensemble_methods': ['weighted_average', 'consensus_checking'],
            'features': [
                'Engine-specific weighting',
                'Method-based confidence bonuses',
                'Data quality assessment',
                'Ensemble confidence calculation',
                'Historical feedback calibration',
                'Performance trend analysis',
                'Automatic weight adjustment suggestions'
            ]
        }
