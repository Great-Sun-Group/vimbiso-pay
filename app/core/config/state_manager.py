"""State management with clear boundaries

This module provides state management with:
- Single source of truth
- Clear boundaries
- Simple validation
- Minimal nesting
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import ComponentException
from django.core.cache import caches

from .atomic_state import AtomicStateManager
from .state_utils import (clear_flow_state, update_flow_data,
                          update_flow_state, update_state_core)

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state with clear boundaries"""

    def __init__(self, key_prefix: str):
        """Initialize state manager

        Args:
            key_prefix: Redis key prefix (must start with 'channel:')

        Raises:
            ComponentException: If key prefix format is invalid
        """
        if not key_prefix or not key_prefix.startswith("channel:"):
            raise ComponentException(
                message="Invalid key prefix format",
                component="state_manager",
                field="key_prefix",
                value=str(key_prefix)
            )

        self.key_prefix = key_prefix
        self.atomic_state = AtomicStateManager(caches['state'])
        self._state = self._initialize_state()

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state structure"""
        # Get channel ID from prefix
        channel_id = self.key_prefix.split(":", 1)[1]

        # Create initial state with metadata
        initial_state = {
            "channel": {
                "type": "whatsapp",
                "identifier": channel_id
            },
            "_metadata": {
                "initialized_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        }

        # Get existing state
        try:
            logger.debug(f"Attempting to get state for key: {self.key_prefix}")
            state_data = self.atomic_state.atomic_get(self.key_prefix)
            logger.debug(f"Retrieved state data: {state_data}")
        except Exception as e:
            # Handle error through ErrorHandler
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_INIT_ERROR",
                    "service": "state_manager",
                    "action": "initialize",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_error(e, self, error_context)

        # Use existing or initial state
        result = state_data or initial_state
        logger.debug(f"Using state: {result}")
        return result

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with validation

        Args:
            updates: State updates to apply

        Raises:
            ComponentException: If updates format is invalid
        """
        if not isinstance(updates, dict):
            raise ComponentException(
                message="Updates must be a dictionary",
                component="state_manager",
                field="updates",
                value=str(type(updates))
            )

        try:
            # Add metadata to updates
            updates["_metadata"] = {
                "updated_at": datetime.utcnow().isoformat()
            }

            # Update local state
            update_state_core(self, updates)

            # Persist to Redis
            logger.debug(f"Persisting state to Redis for key {self.key_prefix}: {self._state}")
            self.atomic_state.atomic_update(self.key_prefix, self._state)
            logger.debug("State persisted successfully")
        except Exception as e:
            # Handle error through ErrorHandler
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_UPDATE_ERROR",
                    "service": "state_manager",
                    "action": "update",
                    "updates": list(updates.keys()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_error(e, self, error_context)

    def get(self, key: str) -> Any:
        """Get state value with validation tracking

        Args:
            key: State key to get

        Returns:
            Value for key or None

        Raises:
            ComponentException: If key format is invalid
        """
        if not key or not isinstance(key, str):
            raise ComponentException(
                message="Key must be a non-empty string",
                component="state_manager",
                field="key",
                value=str(key),
                validation={
                    "in_progress": False,
                    "error": "Invalid key format",
                    "attempts": self._state.get("validation_attempts", {}).get(key, 0) + 1,
                    "last_attempt": datetime.utcnow().isoformat()
                }
            )

        # Track validation attempt
        validation_attempts = self._state.get("validation_attempts", {})
        validation_attempts[key] = validation_attempts.get(key, 0) + 1
        self._state["validation_attempts"] = validation_attempts

        return self._state.get(key)

    # Flow state methods

    def get_flow_state(self) -> Optional[Dict[str, Any]]:
        """Get current flow state"""
        return self.get("flow_data")

    def get_flow_type(self) -> Optional[str]:
        """Get current flow type"""
        flow_data = self.get_flow_state()
        return flow_data.get("flow_type") if flow_data else None

    def get_current_step(self) -> Optional[str]:
        """Get current step for flow routing"""
        flow_data = self.get_flow_state()
        return flow_data.get("step") if flow_data else None

    def get_flow_data(self) -> Dict[str, Any]:
        """Get current flow data"""
        flow_data = self.get_flow_state()
        return flow_data.get("data", {}) if flow_data else {}

    def update_flow_state(
        self,
        flow_type: str,
        step: str,
        data: Optional[Dict] = None
    ) -> None:
        """Update flow state with validation and progress tracking

        Args:
            flow_type: Type of flow
            step: Current step
            data: Optional flow data

        Raises:
            Exception: If flow state update fails (handled by ErrorHandler)
        """
        # Get current flow state for progress tracking
        current_flow = self.get_flow_state() or {}
        current_step_index = current_flow.get("step_index", 0)
        total_steps = current_flow.get("total_steps", 1)

        # Track validation attempt
        validation_state = {
            "in_progress": True,
            "attempts": current_flow.get("validation_attempts", 0) + 1,
            "last_attempt": {
                "flow_type": flow_type,
                "step": step,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        try:
            # Update flow state - will raise exception on failure
            update_flow_state(self, flow_type, step, {
                **(data or {}),
                "step_index": current_step_index + 1,
                "total_steps": total_steps,
                "validation": validation_state,
                "_metadata": {
                    "updated_at": datetime.utcnow().isoformat()
                }
            })

            # Update validation state on success
            validation_state.update({
                "in_progress": False,
                "error": None,
                "completed_at": datetime.utcnow().isoformat()
            })

        except Exception as e:
            # Handle error through ErrorHandler
            error_context = ErrorContext(
                error_type="flow",
                message=str(e),
                details={
                    "step": step,
                    "action": "update_state",
                    "flow_type": flow_type,
                    "validation": validation_state,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_error(e, self, error_context)

    def update_flow_data(self, data: Dict[str, Any]) -> None:
        """Update flow data

        Args:
            data: Flow data updates

        Raises:
            Exception: If flow data update fails (handled by ErrorHandler)
        """
        # Update flow data - will raise exception on failure
        update_flow_data(self, data)

    def clear_flow_state(self) -> None:
        """Clear flow state

        Raises:
            Exception: If flow state clear fails (handled by ErrorHandler)
        """
        # Clear flow state - will raise exception on failure
        clear_flow_state(self)

    def clear_all_state(self) -> None:
        """Clear all state data except channel info

        Resets state to initial with just channel info.
        Clears all other data including flow state, validation state, metadata, etc.

        Raises:
            Exception: If state clear fails (handled by ErrorHandler)
        """
        try:
            # Get channel info to preserve
            channel = self.get("channel")

            # Reset to initial state
            self._state = {
                "channel": channel,
                "_metadata": {
                    "initialized_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            }

            # Persist to Redis
            logger.debug(f"Persisting cleared state to Redis for key {self.key_prefix}: {self._state}")
            self.atomic_state.atomic_update(self.key_prefix, self._state)
            logger.debug("State cleared successfully")

        except Exception as e:
            # Handle error through ErrorHandler
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_CLEAR_ERROR",
                    "service": "state_manager",
                    "action": "clear_all",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_error(e, self, error_context)

    # Channel methods

    def get_channel_id(self) -> str:
        """Get channel identifier

        Returns:
            Channel ID string

        Raises:
            ComponentException: If channel identifier not found
        """
        channel = self.get("channel")
        if not channel or not channel.get("identifier"):
            raise ComponentException(
                message="Channel identifier not found",
                component="state_manager",
                field="channel.identifier",
                value=str(channel)
            )
        return channel["identifier"]

    def get_channel_type(self) -> str:
        """Get channel type

        Returns:
            Channel type string

        Raises:
            ComponentException: If channel type not found
        """
        channel = self.get("channel")
        if not channel or not channel.get("type"):
            raise ComponentException(
                message="Channel type not found",
                component="state_manager",
                field="channel.type",
                value=str(channel)
            )
        return channel["type"]

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token

        Returns:
            bool: True if authenticated with valid token, False otherwise
        """
        try:
            # Check for member_id and token
            member_id = self.get("member_id")
            jwt_token = self.get("jwt_token")
            if not member_id or not jwt_token:
                return False

            # Validate token expiry locally
            from jwt import decode, InvalidTokenError
            from decouple import config
            try:
                # Decode token and check expiry
                decode(jwt_token, config("JWT_SECRET"), algorithms=["HS256"])
                return True
            except InvalidTokenError:
                return False

        except Exception:
            # Any error means not authenticated
            return False

    def get_member_id(self) -> Optional[str]:
        """Get member ID if authenticated

        Returns:
            Member ID string if authenticated with valid token, None otherwise
        """
        # Only return member_id if authenticated with valid token
        return self.get("member_id") if self.is_authenticated() else None
