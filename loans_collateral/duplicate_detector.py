"""
Collateral Duplication Detection System

This module provides comprehensive duplicate detection for collateral items
based on multiple criteria and similarity matching algorithms.
"""

import re
from difflib import SequenceMatcher
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import Collateral


class CollateralDuplicateDetector:
    """
    Advanced duplicate detection system for collateral items.
    
    Detection Strategies:
    1. Exact matches (VIN, License Plate, Registration Number)
    2. High similarity matches (Title, Description, Owner)
    3. Value-based matches (Similar values + location)
    4. Vehicle-specific matches (Make/Model/Year combination)
    5. Temporal proximity (Recent similar entries)
    """
    
    # Similarity thresholds (0.0 to 1.0)
    EXACT_MATCH_THRESHOLD = 1.0
    HIGH_SIMILARITY_THRESHOLD = 0.85
    MEDIUM_SIMILARITY_THRESHOLD = 0.70
    LOW_SIMILARITY_THRESHOLD = 0.60
    
    # Value proximity threshold (percentage)
    VALUE_PROXIMITY_THRESHOLD = 0.15  # 15% difference
    
    def __init__(self, exclude_collateral_id=None):
        """
        Initialize the duplicate detector.
        
        Args:
            exclude_collateral_id: Collateral ID to exclude from checks (for updates)
        """
        self.exclude_collateral_id = exclude_collateral_id
        self.detection_results = []
    
    def detect_duplicates(self, collateral_data, include_potential=True):
        """
        Main method to detect potential duplicates.
        
        Args:
            collateral_data: Dictionary containing collateral information
            include_potential: Whether to include potential (lower confidence) matches
            
        Returns:
            Dictionary containing detected duplicates categorized by confidence level
        """
        self.detection_results = []
        
        # Get base queryset (exclude current collateral if updating)
        queryset = Collateral.objects.all()
        if self.exclude_collateral_id:
            queryset = queryset.exclude(collateral_id=self.exclude_collateral_id)
        
        # 1. Check for exact matches (highest priority)
        self._check_exact_matches(queryset, collateral_data)
        
        # 2. Check for high similarity matches
        self._check_high_similarity_matches(queryset, collateral_data)
        
        # 3. Check for vehicle-specific duplicates
        if self._is_vehicle_collateral(collateral_data):
            self._check_vehicle_duplicates(queryset, collateral_data)
        
        # 4. Check for value-based potential duplicates
        if include_potential:
            self._check_value_based_duplicates(queryset, collateral_data)
        
        # 5. Check temporal proximity
        if include_potential:
            self._check_temporal_duplicates(queryset, collateral_data)
        
        # Categorize and return results
        return self._categorize_results()
    
    def _check_exact_matches(self, queryset, data):
        """Check for exact matches on unique identifiers"""
        exact_matches = []
        
        # Check VIN (Vehicle Identification Number)
        if data.get('vehicle_vin'):
            vin_matches = queryset.filter(
                vehicle_vin__iexact=data['vehicle_vin']
            ).select_related('loan_application__customer', 'collateral_type')
            
            for match in vin_matches:
                exact_matches.append({
                    'collateral': match,
                    'match_type': 'exact_vin',
                    'match_field': 'vehicle_vin',
                    'confidence': 1.0,
                    'reason': f'Identical VIN: {data["vehicle_vin"]}',
                    'risk_level': 'high'
                })
        
        # Check License Plate
        if data.get('vehicle_license_plate'):
            plate_matches = queryset.filter(
                vehicle_license_plate__iexact=data['vehicle_license_plate']
            ).select_related('loan_application__customer', 'collateral_type')
            
            for match in plate_matches:
                exact_matches.append({
                    'collateral': match,
                    'match_type': 'exact_license_plate',
                    'match_field': 'vehicle_license_plate',
                    'confidence': 1.0,
                    'reason': f'Identical License Plate: {data["vehicle_license_plate"]}',
                    'risk_level': 'high'
                })
        
        # Check Registration Number
        if data.get('registration_number'):
            reg_matches = queryset.filter(
                registration_number__iexact=data['registration_number']
            ).select_related('loan_application__customer', 'collateral_type')
            
            for match in reg_matches:
                exact_matches.append({
                    'collateral': match,
                    'match_type': 'exact_registration',
                    'match_field': 'registration_number',
                    'confidence': 1.0,
                    'reason': f'Identical Registration: {data["registration_number"]}',
                    'risk_level': 'high'
                })
        
        self.detection_results.extend(exact_matches)
    
    def _check_high_similarity_matches(self, queryset, data):
        """Check for high similarity matches on textual fields"""
        if not data.get('title') or not data.get('owner_name'):
            return
        
        # Get potential matches with similar titles
        potential_matches = queryset.filter(
            Q(title__icontains=data['title'][:20]) |
            Q(owner_name__icontains=data['owner_name'][:20])
        ).select_related('loan_application__customer', 'collateral_type')
        
        for match in potential_matches:
            # Calculate title similarity
            title_similarity = self._calculate_similarity(
                data.get('title', ''), match.title
            )
            
            # Calculate owner similarity
            owner_similarity = self._calculate_similarity(
                data.get('owner_name', ''), match.owner_name
            )
            
            # Calculate description similarity if available
            description_similarity = 0.0
            if data.get('description') and match.description:
                description_similarity = self._calculate_similarity(
                    data['description'], match.description
                )
            
            # Weighted similarity score
            overall_similarity = (
                title_similarity * 0.4 +
                owner_similarity * 0.4 +
                description_similarity * 0.2
            )
            
            if overall_similarity >= self.HIGH_SIMILARITY_THRESHOLD:
                risk_level = 'high' if overall_similarity >= 0.95 else 'medium'
                
                self.detection_results.append({
                    'collateral': match,
                    'match_type': 'high_similarity',
                    'match_field': 'title_owner',
                    'confidence': overall_similarity,
                    'reason': f'High similarity: Title ({title_similarity:.1%}), Owner ({owner_similarity:.1%})',
                    'risk_level': risk_level,
                    'details': {
                        'title_similarity': title_similarity,
                        'owner_similarity': owner_similarity,
                        'description_similarity': description_similarity
                    }
                })
    
    def _check_vehicle_duplicates(self, queryset, data):
        """Check for vehicle-specific duplicates"""
        if not all([data.get('vehicle_make'), data.get('vehicle_model'), data.get('vehicle_year')]):
            return
        
        # Look for similar vehicles
        vehicle_matches = queryset.filter(
            vehicle_make__iexact=data['vehicle_make'],
            vehicle_model__iexact=data['vehicle_model'],
            vehicle_year=data['vehicle_year'],
            collateral_type__category='vehicle'
        ).select_related('loan_application__customer', 'collateral_type')
        
        for match in vehicle_matches:
            # Additional similarity checks
            location_similarity = 0.0
            if data.get('location') and match.location:
                location_similarity = self._calculate_similarity(
                    data['location'], match.location
                )
            
            # Check value proximity
            value_similarity = 0.0
            if data.get('declared_value') and match.declared_value:
                value_diff = abs(float(data['declared_value']) - float(match.declared_value))
                value_avg = (float(data['declared_value']) + float(match.declared_value)) / 2
                value_similarity = 1.0 - (value_diff / value_avg) if value_avg > 0 else 0.0
                value_similarity = max(0.0, value_similarity)
            
            # Calculate overall vehicle similarity
            vehicle_similarity = 0.8  # Base similarity for make/model/year match
            if location_similarity > 0.6:
                vehicle_similarity += 0.1
            if value_similarity > 0.8:
                vehicle_similarity += 0.1
            
            risk_level = 'high' if vehicle_similarity >= 0.9 else 'medium'
            
            self.detection_results.append({
                'collateral': match,
                'match_type': 'vehicle_duplicate',
                'match_field': 'vehicle_details',
                'confidence': vehicle_similarity,
                'reason': f'Same vehicle: {data["vehicle_make"]} {data["vehicle_model"]} {data["vehicle_year"]}',
                'risk_level': risk_level,
                'details': {
                    'location_similarity': location_similarity,
                    'value_similarity': value_similarity
                }
            })
    
    def _check_value_based_duplicates(self, queryset, data):
        """Check for duplicates based on value and location proximity"""
        if not data.get('declared_value'):
            return
        
        declared_value = float(data['declared_value'])
        value_range = declared_value * self.VALUE_PROXIMITY_THRESHOLD
        
        # Find collaterals with similar values
        value_matches = queryset.filter(
            declared_value__range=[
                declared_value - value_range,
                declared_value + value_range
            ],
            collateral_type=data.get('collateral_type')
        ).select_related('loan_application__customer', 'collateral_type')
        
        for match in value_matches:
            # Check location similarity if available
            location_similarity = 0.0
            if data.get('location') and match.location:
                location_similarity = self._calculate_similarity(
                    data['location'], match.location
                )
            
            # Skip if location similarity is too low
            if location_similarity < self.LOW_SIMILARITY_THRESHOLD:
                continue
            
            # Calculate value proximity
            value_diff = abs(declared_value - float(match.declared_value))
            value_proximity = 1.0 - (value_diff / declared_value)
            
            overall_similarity = (location_similarity * 0.6) + (value_proximity * 0.4)
            
            if overall_similarity >= self.MEDIUM_SIMILARITY_THRESHOLD:
                self.detection_results.append({
                    'collateral': match,
                    'match_type': 'value_location',
                    'match_field': 'value_location',
                    'confidence': overall_similarity,
                    'reason': f'Similar value (${declared_value:,.0f}) and location',
                    'risk_level': 'medium',
                    'details': {
                        'value_proximity': value_proximity,
                        'location_similarity': location_similarity
                    }
                })
    
    def _check_temporal_duplicates(self, queryset, data):
        """Check for recent similar entries (potential re-submissions)"""
        # Look for recent collaterals (last 30 days)
        recent_cutoff = timezone.now() - timedelta(days=30)
        recent_collaterals = queryset.filter(
            created_at__gte=recent_cutoff
        ).select_related('loan_application__customer', 'collateral_type')
        
        for match in recent_collaterals:
            # Check if they're from the same customer
            if (data.get('loan_application') and 
                hasattr(match, 'loan_application') and
                match.loan_application.customer == data['loan_application'].customer):
                
                # Check similarity of titles and types
                title_similarity = 0.0
                if data.get('title'):
                    title_similarity = self._calculate_similarity(
                        data['title'], match.title
                    )
                
                type_match = (data.get('collateral_type') == match.collateral_type)
                
                if title_similarity >= self.MEDIUM_SIMILARITY_THRESHOLD or type_match:
                    confidence = title_similarity if title_similarity > 0.5 else 0.6
                    
                    self.detection_results.append({
                        'collateral': match,
                        'match_type': 'temporal_duplicate',
                        'match_field': 'recent_similar',
                        'confidence': confidence,
                        'reason': f'Recent similar collateral from same customer (created {match.created_at.strftime("%Y-%m-%d")})',
                        'risk_level': 'medium',
                        'details': {
                            'days_ago': (timezone.now() - match.created_at).days,
                            'title_similarity': title_similarity,
                            'same_type': type_match
                        }
                    })
    
    def _calculate_similarity(self, str1, str2):
        """Calculate similarity between two strings using SequenceMatcher"""
        if not str1 or not str2:
            return 0.0
        
        # Normalize strings
        str1_clean = re.sub(r'[^\w\s]', '', str1.lower().strip())
        str2_clean = re.sub(r'[^\w\s]', '', str2.lower().strip())
        
        return SequenceMatcher(None, str1_clean, str2_clean).ratio()
    
    def _is_vehicle_collateral(self, data):
        """Check if the collateral is vehicle-type"""
        collateral_type = data.get('collateral_type')
        return (collateral_type and 
                hasattr(collateral_type, 'category') and 
                collateral_type.category == 'vehicle')
    
    def _categorize_results(self):
        """Categorize detection results by confidence and risk level"""
        categorized = {
            'exact_matches': [],      # Confidence >= 1.0
            'high_probability': [],   # Confidence >= 0.85
            'medium_probability': [], # Confidence >= 0.70
            'low_probability': [],    # Confidence >= 0.60
            'total_count': len(self.detection_results),
            'has_high_risk': False
        }
        
        for result in self.detection_results:
            confidence = result['confidence']
            
            # Check for high risk indicators
            if result['risk_level'] == 'high':
                categorized['has_high_risk'] = True
            
            # Categorize by confidence level
            if confidence >= self.EXACT_MATCH_THRESHOLD:
                categorized['exact_matches'].append(result)
            elif confidence >= self.HIGH_SIMILARITY_THRESHOLD:
                categorized['high_probability'].append(result)
            elif confidence >= self.MEDIUM_SIMILARITY_THRESHOLD:
                categorized['medium_probability'].append(result)
            elif confidence >= self.LOW_SIMILARITY_THRESHOLD:
                categorized['low_probability'].append(result)
        
        return categorized


def detect_collateral_duplicates(collateral_data, exclude_id=None):
    """
    Convenience function to detect collateral duplicates.
    
    Args:
        collateral_data: Dictionary containing collateral information
        exclude_id: Collateral ID to exclude from checks
        
    Returns:
        Dictionary containing categorized duplicate detection results
    """
    detector = CollateralDuplicateDetector(exclude_collateral_id=exclude_id)
    return detector.detect_duplicates(collateral_data)


def check_duplicate_risk_level(duplicate_results):
    """
    Assess the overall risk level based on duplicate detection results.
    
    Args:
        duplicate_results: Results from detect_collateral_duplicates()
        
    Returns:
        String indicating risk level: 'high', 'medium', 'low', or 'none'
    """
    if duplicate_results['exact_matches']:
        return 'high'
    elif duplicate_results['high_probability']:
        return 'high'
    elif duplicate_results['medium_probability']:
        return 'medium'
    elif duplicate_results['low_probability']:
        return 'low'
    else:
        return 'none'
