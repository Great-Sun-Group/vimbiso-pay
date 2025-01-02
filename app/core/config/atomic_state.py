from django.core.cache import cache
from typing import Any, Dict, Optional, Tuple


class AtomicStateManager:
    """Atomic state manager using Django cache"""

    def __init__(self, cache_backend):
        self.cache = cache_backend

    def atomic_get(self, key: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            state_data = self.cache.get(key)
            return state_data, None
        except Exception as e:
            return None, str(e)

    def atomic_set(self, key: str, value: Dict[str, Any], ttl: int = 300) -> Optional[str]:
        try:
            self.cache.set(key, value, timeout=ttl)
            return None
        except Exception as e:
            return str(e)
        
    def atomic_update(self, key: str, value: Dict[str, Any], ttl: int = 300) -> Tuple[bool, Optional[str]]:
        try:
            self.cache.set(key, value, timeout=ttl)
            return True, None
        except Exception as e:
            return False, str(e)