"""Redis atomic operations for state management"""
import json
import logging
from typing import Any, Dict, Optional

from redis import Redis, WatchError

from .exceptions import SystemException

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
    ) -> None:
        """Atomically update state components in Redis

        Args:
            key_prefix: Redis key prefix
            state: State data to store
            ttl: Time to live in seconds
            max_retries: Maximum number of retry attempts

        Raises:
            SystemException: If update fails or max retries exceeded
        """
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Start pipeline with optimistic locking
                pipe = self.redis.pipeline()
                pipe.watch(key_prefix)

                try:
                    # Start transaction
                    pipe.multi()

                    # Store state with TTL (already validated by state_manager)
                    state_json = json.dumps(state)
                    logger.debug(f"Storing validated state with TTL {ttl}")
                    pipe.setex(key_prefix, ttl, state_json)

                    # Execute transaction
                    pipe.execute()
                    return

                except WatchError:
                    logger.warning(
                        f"Concurrent modification detected for {key_prefix}, "
                        f"retry {retry_count + 1}/{max_retries}"
                    )
                    retry_count += 1
                    continue

                except Exception as e:
                    logger.error(f"Transaction error: {str(e)}")
                    raise SystemException(
                        message=f"Transaction failed: {str(e)}",
                        code="REDIS_TRANSACTION_ERROR",
                        service="redis_atomic",
                        action="update"
                    )

                finally:
                    pipe.reset()

            except Exception as e:
                logger.error(f"Redis operation error: {str(e)}")
                raise SystemException(
                    message=f"Redis operation failed: {str(e)}",
                    code="REDIS_OPERATION_ERROR",
                    service="redis_atomic",
                    action="update"
                )

        raise SystemException(
            message="Max retries exceeded for atomic update",
            code="REDIS_MAX_RETRIES",
            service="redis_atomic",
            action="update"
        )

    def atomic_get(
        self,
        key_prefix: str
    ) -> Optional[Dict[str, Any]]:
        """Atomically get state from Redis

        Args:
            key_prefix: Redis key prefix

        Returns:
            State data if found, None if not found

        Raises:
            SystemException: If get operation fails
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
                    return None

                try:
                    # Parse state (validation handled by state_manager)
                    state = json.loads(result[0])
                    return state
                except json.JSONDecodeError:
                    logger.error("Failed to parse state data from Redis")
                    raise SystemException(
                        message="Invalid state data format",
                        code="REDIS_INVALID_DATA",
                        service="redis_atomic",
                        action="get"
                    )

            except WatchError:
                logger.warning(f"Concurrent modification detected for {key_prefix}")
                raise SystemException(
                    message="Concurrent modification detected",
                    code="REDIS_CONCURRENT_MOD",
                    service="redis_atomic",
                    action="get"
                )

            finally:
                pipe.reset()

        except Exception as e:
            logger.error(f"Redis get operation error: {str(e)}")
            raise SystemException(
                message=f"Redis get operation failed: {str(e)}",
                code="REDIS_GET_ERROR",
                service="redis_atomic",
                action="get"
            )

    def atomic_delete(
        self,
        key_prefix: str
    ) -> None:
        """Atomically delete state from Redis

        Args:
            key_prefix: Redis key prefix

        Raises:
            SystemException: If delete operation fails
        """
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
                return

            except Exception as e:
                logger.error(f"Delete transaction error: {str(e)}")
                raise SystemException(
                    message=f"Delete failed: {str(e)}",
                    code="REDIS_DELETE_ERROR",
                    service="redis_atomic",
                    action="delete"
                )

            finally:
                pipe.reset()

        except Exception as e:
            logger.error(f"Redis delete operation error: {str(e)}")
            raise SystemException(
                message=f"Redis delete operation failed: {str(e)}",
                code="REDIS_DELETE_ERROR",
                service="redis_atomic",
                action="delete"
            )
