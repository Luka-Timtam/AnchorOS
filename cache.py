import time
import logging

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
    
    def clear(self):
        count = len(self._cache)
        self._cache = {}
        if count > 0:
            logger.debug(f"[Cache CLEAR] {count} entries removed")


cache = InMemoryCache(default_ttl=60)


CACHE_KEY_LIFETIME_REVENUE = 'dashboard:lifetime_revenue'
CACHE_KEY_DASHBOARD_CHARTS = 'dashboard:charts'
CACHE_KEY_MRR = 'dashboard:mrr'


def clear_all_cache():
    cache.clear()
