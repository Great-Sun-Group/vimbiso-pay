"""Redis atomic operations for state management"""
import json
import logging
from typing import Any, Dict, Optional, Tuple

from redis import Redis, WatchError

logger = logging.getLogger(__name__)


class AtomicStateManager:
    """Manages atomic state operations with Redis"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def atomic_update(
        self,
        key_prefix: str,
        state: Dict[str, Any],
        ttl: int,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str]]:
        """Atomically update state components in Redis
        Returns (success, error_message)"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Start pipeline with optimistic locking
                pipe = self.redis.pipeline()
                pipe.watch(key_prefix)

                try:
                    # Start transaction
                    pipe.multi()

                    # Store state with TTL
                    state_json = json.dumps(state)
                    logger.debug(f"Storing state with TTL {ttl}")
                    pipe.setex(key_prefix, ttl, state_json)

                    # Execute transaction
                    pipe.execute()
                    return True, None

                except WatchError:
                    logger.warning(
                        f"Concurrent modification detected for {key_prefix}, "
                        f"retry {retry_count + 1}/{max_retries}"
                    )
                    retry_count += 1
                    continue

                except Exception as e:
                    logger.error(f"Transaction error: {str(e)}")
                    return False, f"Transaction failed: {str(e)}"

                finally:
                    pipe.reset()

            except Exception as e:
                logger.error(f"Redis operation error: {str(e)}")
                return False, f"Redis operation failed: {str(e)}"

        return False, "Max retries exceeded for atomic update"

    def atomic_get(
        self,
        key_prefix: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Atomically get state
        Returns (state_data, error_message)
        """
        try:
            # Get state
            pipe = self.redis.pipeline()
            try:
                # Queue get operation
                pipe.get(key_prefix)

                # Execute and get result
                result = pipe.execute()

                if not result or not result[0]:
                    return None, None

                try:
                    state = json.loads(result[0])
                except json.JSONDecodeError:
                    return None, "Invalid state data format"

                return state, None

            except WatchError:
                logger.warning(f"Concurrent modification detected for {key_prefix}")
                return None, "Concurrent modification"

            finally:
                pipe.reset()

        except Exception as e:
            logger.error(f"Redis get operation error: {str(e)}")
            return None, f"Redis get operation failed: {str(e)}"

    def atomic_delete(
        self,
        key_prefix: str
    ) -> Tuple[bool, Optional[str]]:
        """Atomically delete state from Redis
        Returns (success, error_message)"""
        try:
            # Start pipeline with optimistic locking
            pipe = self.redis.pipeline()
            pipe.watch(key_prefix)

            try:
                # Start transaction
                pipe.multi()

                # Delete state
                pipe.delete(key_prefix)

                # Execute transaction
                pipe.execute()
                return True, None

            except Exception as e:
                logger.error(f"Delete transaction error: {str(e)}")
                return False, f"Delete failed: {str(e)}"

            finally:
                pipe.reset()

        except Exception as e:
            logger.error(f"Redis delete operation error: {str(e)}")
            return False, f"Redis delete operation failed: {str(e)}"
