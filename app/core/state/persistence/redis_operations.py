"""Redis persistence layer for schema-validated state

This module provides atomic Redis operations for storing and retrieving state.
All state is schema-validated at a higher level - this layer only handles
persistence of the validated state.

Note: The _validation field is stripped before storage since validation state
is not persisted (components can store their own data in component_data.data).
"""
import json
import logging
from typing import Any, Dict, Optional, Tuple

from redis import Redis, WatchError

logger = logging.getLogger(__name__)


class RedisAtomic:
    """Atomic Redis operations for schema-validated state persistence"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def execute_atomic(
        self,
        key: str,
        operation: str,
        value: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Execute atomic Redis operation

        Args:
            key: Redis key
            operation: Operation type ('get', 'set', 'delete')
            value: Optional value for set operation
            ttl: Optional TTL for set operation
            max_retries: Maximum retry attempts for set/delete

        Returns:
            Tuple of (success, result_data, error_message)
        """
        retry_count = 0
        while retry_count < max_retries:
            try:
                pipe = self.redis.pipeline()
                pipe.watch(key)

                try:
                    pipe.multi()

                    if operation == 'get':
                        pipe.get(key)
                        result = pipe.execute()
                        if not result or not result[0]:
                            return True, None, None
                        data = json.loads(result[0])
                        # Strip validation state since it's not persisted
                        # (Schema validation happens at state manager level)
                        if "_validation" in data:
                            del data["_validation"]
                        return True, data, None

                    elif operation == 'set':
                        if value is None or ttl is None:
                            return False, None, "Missing value or TTL for set operation"
                        # Strip validation state before storage
                        # (Components can store their own data in component_data.data)
                        store_value = value.copy()
                        if "_validation" in store_value:
                            del store_value["_validation"]
                        pipe.setex(key, ttl, json.dumps(store_value))
                        pipe.execute()
                        return True, None, None

                    elif operation == 'delete':
                        pipe.delete(key)
                        pipe.execute()
                        return True, None, None

                    else:
                        return False, None, f"Unknown operation: {operation}"

                except WatchError:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Retry {retry_count + 1}/{max_retries}")
                    retry_count += 1
                    continue

                except json.JSONDecodeError:
                    return False, None, "Invalid JSON data"

                finally:
                    pipe.reset()

            except Exception as e:
                return False, None, str(e)

        return False, None, "Max retries exceeded"
