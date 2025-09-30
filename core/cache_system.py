"""
Redis Cache Configuration for Loan Management System
Provides intelligent caching for expensive operations
"""

import redis
import json
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class LoanSystemCache:
    """Advanced caching system for loan management operations"""
    
    def __init__(self):
        # Use Django cache backend (works with both Redis and memory)
        self.cache = cache
        self.redis_client = None  # Not needed when using Django cache
        
        # Performance statistics
        self.stats = {
            'hits': 0,
            'misses': 0, 
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        
        # Cache timeouts
        self.default_timeout = 600  # 10 minutes
        self.list_timeout = 300     # 5 minutes
        
        logger.info("✅ Loan cache system initialized with Django cache backend")
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate unique cache key from parameters"""
        # Sort kwargs for consistent key generation
        key_data = f"{prefix}:" + ":".join([f"{k}={v}" for k, v in sorted(kwargs.items())])
        # Hash long keys to keep them manageable
        if len(key_data) > 200:
            hash_obj = hashlib.md5(key_data.encode())
            return f"{prefix}:{hash_obj.hexdigest()}"
        return key_data
    
    def _serialize_data(self, data):
        """Serialize data for Redis storage"""
        def decimal_handler(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(data, default=decimal_handler)
    
    def _deserialize_data(self, data_str):
        """Deserialize data from Redis"""
        if not data_str:
            return None
        return json.loads(data_str)
    
    def set_cache(self, key: str, data, expiry_seconds: int = 3600):
        """Set cache value with expiration"""
        try:
            # Use Django cache directly (supports both Redis and memory backends)
            self.cache.set(key, data, expiry_seconds)
            self.stats['sets'] += 1
            logger.debug(f"📦 Cached: {key[:50]}... for {expiry_seconds}s")
            return True
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"❌ Cache set failed for {key}: {e}")
            return False
    
    def get_cache(self, key: str):
        """Get cache value"""
        try:
            # Use Django cache directly
            data = self.cache.get(key)
            if data is not None:
                self.stats['hits'] += 1
                logger.debug(f"🎯 Cache hit: {key[:50]}...")
                return data
            else:
                self.stats['misses'] += 1 
                logger.debug(f"❌ Cache miss: {key[:50]}...")
                return None
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"❌ Cache get failed for {key}: {e}")
            return None
    
    def delete_cache(self, pattern: str = None, key: str = None):
        """Delete cache by pattern or specific key"""
        try:
            if key:
                # Use Django cache delete
                self.cache.delete(key)
                self.stats['deletes'] += 1
                logger.debug(f"🗑️ Deleted cache: {key}")
                return True
            
            if pattern:
                # Pattern deletion not supported with Django cache
                # This would require Redis-specific functionality
                logger.warning("Pattern deletion not supported with Django cache backend")
                return False
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"❌ Cache delete failed: {e}")
            return False
    
    def cache_approval_progress(self, application_id: int, progress_data: dict):
        """Cache approval progress for an application"""
        cache_key = self._generate_cache_key("approval_progress", app_id=application_id)
        
        # Add timestamp for cache freshness tracking
        cached_data = {
            'progress': progress_data,
            'cached_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        # Cache for 10 minutes (600 seconds)
        return self.set_cache(cache_key, cached_data, 600)
    
    def get_cached_approval_progress(self, application_id: int):
        """Get cached approval progress"""
        cache_key = self._generate_cache_key("approval_progress", app_id=application_id)
        cached_data = self.get_cache(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            return cached_data.get('progress')
        return None
    
    def invalidate_approval_progress(self, application_id: int):
        """Invalidate approval progress cache when payments change"""
        cache_key = self._generate_cache_key("approval_progress", app_id=application_id)
        self.delete_cache(key=cache_key)
        logger.info(f"🔄 Invalidated approval progress cache for app {application_id}")
    
    def cache_application_list(self, company_id: int, filters: dict, data: list):
        """Cache applications list with filters"""
        cache_key = self._generate_cache_key(
            "applications_list", 
            company_id=company_id, 
            **filters
        )
        
        cached_data = {
            'applications': data,
            'cached_at': datetime.now().isoformat(),
            'count': len(data)
        }
        
        # Cache for 5 minutes (300 seconds) - shorter for list data
        return self.set_cache(cache_key, cached_data, 300)
    
    def get_cached_application_list(self, company_id: int, filters: dict):
        """Get cached applications list"""
        cache_key = self._generate_cache_key(
            "applications_list", 
            company_id=company_id, 
            **filters
        )
        cached_data = self.get_cache(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            return cached_data.get('applications')
        return None
    
    def cache_payment_statistics(self, company_id: int, stats: dict):
        """Cache payment statistics"""
        cache_key = self._generate_cache_key("payment_stats", company_id=company_id)
        
        cached_data = {
            'stats': stats,
            'cached_at': datetime.now().isoformat()
        }
        
        # Cache for 15 minutes (900 seconds)
        return self.set_cache(cache_key, cached_data, 900)
    
    def get_cached_payment_statistics(self, company_id: int):
        """Get cached payment statistics"""
        cache_key = self._generate_cache_key("payment_stats", company_id=company_id)
        cached_data = self.get_cache(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            return cached_data.get('stats')
        return None
    
    def warm_cache_for_company(self, company_id: int):
        """Pre-warm cache with commonly accessed data"""
        logger.info(f"🔥 Starting cache warm-up for company {company_id}")
        
        try:
            # This would be called by background task
            from loans_core.models import LoanApplication
            
            # Pre-calculate approval progress for active applications
            active_apps = LoanApplication.objects.filter(
                company_id=company_id, 
                status='approved'
            )[:50]  # Limit to most recent
            
            cached_count = 0
            for app in active_apps:
                if not self.get_cached_approval_progress(app.id):
                    progress = app.get_approval_progress()
                    if self.cache_approval_progress(app.id, progress):
                        cached_count += 1
            
            logger.info(f"🔥 Cache warm-up complete: {cached_count} items cached")
            return cached_count
            
        except Exception as e:
            logger.error(f"❌ Cache warm-up failed: {e}")
            return 0
    
    def get_cache_stats(self):
        """Get cache performance statistics"""
        stats = {
            'redis_available': self.redis_client is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            if self.redis_client:
                info = self.redis_client.info()
                stats.update({
                    'redis_memory_used': info.get('used_memory_human', 'Unknown'),
                    'redis_keys_count': self.redis_client.dbsize(),
                    'redis_hits': info.get('keyspace_hits', 0),
                    'redis_misses': info.get('keyspace_misses', 0)
                })
                
                # Calculate hit ratio
                hits = info.get('keyspace_hits', 0)
                misses = info.get('keyspace_misses', 0)
                if hits + misses > 0:
                    stats['hit_ratio'] = round(hits / (hits + misses) * 100, 2)
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
        
        return stats

# Global cache instance
loan_cache = LoanSystemCache()
