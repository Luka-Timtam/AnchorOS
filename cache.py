import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class InMemoryCache:
    def __init__(self, default_ttl=30):
        self._cache = {}
        self._default_ttl = default_ttl
    
    def get(self, key):
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry['expires']:
                logger.debug(f"[Cache HIT] {key}")
                return entry['value'], True
            else:
                del self._cache[key]
                logger.debug(f"[Cache EXPIRED] {key}")
        logger.debug(f"[Cache MISS] {key}")
        return None, False
    
    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self._default_ttl
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
        logger.debug(f"[Cache SET] {key} (TTL: {ttl}s)")
    
    def invalidate(self, key):
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"[Cache INVALIDATE] {key}")
    
    def invalidate_prefix(self, prefix):
        keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._cache[key]
        if keys_to_delete:
            logger.debug(f"[Cache INVALIDATE PREFIX] {prefix} ({len(keys_to_delete)} keys)")
    
    def clear(self):
        count = len(self._cache)
        self._cache = {}
        logger.debug(f"[Cache CLEAR] {count} entries removed")


cache = InMemoryCache(default_ttl=30)


CACHE_KEY_DASHBOARD_STATS = 'dashboard:stats'
CACHE_KEY_LIFETIME_REVENUE = 'dashboard:lifetime_revenue'
CACHE_KEY_REVENUE_MILESTONES = 'dashboard:revenue_milestones'
CACHE_KEY_DASHBOARD_CHARTS = 'dashboard:charts'
CACHE_KEY_LEAD_COUNTS = 'dashboard:lead_counts'
CACHE_KEY_OUTREACH_STATS = 'dashboard:outreach'
CACHE_KEY_CLIENT_STATS = 'dashboard:client_stats'
CACHE_KEY_MRR = 'dashboard:mrr'


def invalidate_revenue_cache():
    cache.invalidate(CACHE_KEY_LIFETIME_REVENUE)
    cache.invalidate(CACHE_KEY_REVENUE_MILESTONES)
    cache.invalidate(CACHE_KEY_CLIENT_STATS)
    cache.invalidate(CACHE_KEY_MRR)
    cache.invalidate(CACHE_KEY_DASHBOARD_STATS)
    cache.invalidate(CACHE_KEY_DASHBOARD_CHARTS)
    logger.debug("[Cache] Revenue-related caches invalidated")


def invalidate_client_cache():
    cache.invalidate(CACHE_KEY_CLIENT_STATS)
    cache.invalidate(CACHE_KEY_MRR)
    cache.invalidate(CACHE_KEY_LIFETIME_REVENUE)
    cache.invalidate(CACHE_KEY_DASHBOARD_STATS)
    cache.invalidate(CACHE_KEY_DASHBOARD_CHARTS)
    logger.debug("[Cache] Client-related caches invalidated")


def invalidate_lead_cache():
    cache.invalidate(CACHE_KEY_LEAD_COUNTS)
    cache.invalidate(CACHE_KEY_DASHBOARD_STATS)
    logger.debug("[Cache] Lead-related caches invalidated")


def invalidate_outreach_cache():
    cache.invalidate(CACHE_KEY_OUTREACH_STATS)
    cache.invalidate(CACHE_KEY_DASHBOARD_STATS)
    cache.invalidate(CACHE_KEY_DASHBOARD_CHARTS)
    logger.debug("[Cache] Outreach-related caches invalidated")


def invalidate_freelance_cache():
    cache.invalidate(CACHE_KEY_LIFETIME_REVENUE)
    cache.invalidate(CACHE_KEY_REVENUE_MILESTONES)
    cache.invalidate(CACHE_KEY_DASHBOARD_STATS)
    logger.debug("[Cache] Freelance-related caches invalidated")


def invalidate_all_dashboard_cache():
    cache.invalidate_prefix('dashboard:')
    logger.debug("[Cache] All dashboard caches invalidated")
