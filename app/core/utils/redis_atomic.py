"""Redis atomic operations for state management"""
import json
import logging
from typing import Dict, Any, Optional, Tuple
from redis import Redis, WatchError
from datetime import datetime

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
        stage: Optional[str] = None,
        option: Optional[str] = None,
        direction: Optional[str] = None,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str]]:
        """Atomically update state components in Redis
        Returns (success, error_message)"""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Keys to watch for changes
                keys = [
                    key_prefix,  # Main state
                    f"{key_prefix}_stage",
                    f"{key_prefix}_option",
                    f"{key_prefix}_direction"
                ]

                # Start pipeline with optimistic locking
                pipe = self.redis.pipeline()
                pipe.watch(*keys)

                try:
                    # Add version and timestamp
                    state['_version'] = int(datetime.now().timestamp())
                    state['_last_updated'] = datetime.now().isoformat()

                    # Start transaction
                    pipe.multi()

                    # Store state with TTL
                    state_json = json.dumps(state)
                    logger.debug(f"Storing state with TTL {ttl}")
                    pipe.setex(
                        key_prefix,
                        ttl,
                        state_json
                    )

                    # Set additional fields if provided
                    if stage:
                        pipe.setex(f"{key_prefix}_stage", ttl, stage)
                    if option:
                        pipe.setex(f"{key_prefix}_option", ttl, option)
                    if direction:
                        pipe.setex(f"{key_prefix}_direction", ttl, direction)

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
        key_prefix: str,
        include_metadata: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Atomically get state and metadata
        Returns (state_data, error_message)
        """
        try:
            # Keys to retrieve
            keys = [key_prefix]  # Main state
            if include_metadata:
                keys.extend([
                    f"{key_prefix}_stage",
                    f"{key_prefix}_option",
                    f"{key_prefix}_direction"
                ])

            # Get all values atomically
            pipe = self.redis.pipeline()
            pipe.watch(*keys)

            try:
                # Get values
                values = pipe.mget(keys)
                pipe.unwatch()

                # Process main state
                state_json = values[0]
                if not state_json:
                    return None, None

                try:
                    state = json.loads(state_json)
                except json.JSONDecodeError:
                    return None, "Invalid state data format"

                # Add metadata if requested
                if include_metadata and len(values) > 1:
                    state.update({
                        "_stage": values[1],
                        "_option": values[2],
                        "_direction": values[3]
                    })

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
        """Atomically delete state and metadata from Redis
        Returns (success, error_message)"""
        try:
            # Start pipeline with optimistic locking
            pipe = self.redis.pipeline()
            pipe.watch(key_prefix)

            try:
                # Start transaction
                pipe.multi()

                # Delete all keys
                pipe.delete(
                    key_prefix,
                    f"{key_prefix}_stage",
                    f"{key_prefix}_option",
                    f"{key_prefix}_direction"
                )

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
