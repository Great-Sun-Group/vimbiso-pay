"""State management implementation

This module implements the StateManagerInterface with:
- Single source of truth
- Clear boundaries
- Simple validation
- Minimal nesting
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.error.exceptions import ComponentException
from core.error.handler import ErrorHandler
from core.error.types import ErrorContext
from core.messaging.interface import MessagingServiceInterface
from core.state.persistence.client import get_redis_client

from .atomic_manager import AtomicStateManager
from .interface import StateManagerInterface
from .validator import StateValidator

logger = logging.getLogger(__name__)


class StateManager(StateManagerInterface):
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
        redis_client = get_redis_client()
        self.atomic_state = AtomicStateManager(redis_client)
        self._state = self._initialize_state()
        self._messaging = None  # Will be set by MessagingService

    @property
    def messaging(self) -> MessagingServiceInterface:
        """Get messaging service with validation

        Returns:
            MessagingServiceInterface: Messaging service implementation

        Raises:
            ComponentException: If messaging service not initialized
        """
        if self._messaging is None:
            raise ComponentException(
                message="Messaging service not initialized",
                component="state_manager",
                field="messaging"
            )
        return self._messaging

    @messaging.setter
    def messaging(self, service: MessagingServiceInterface) -> None:
        """Set messaging service

        Args:
            service: Messaging service implementation
        """
        self._messaging = service

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
        state_data = None
        try:
            state_data = self.atomic_state.atomic_get(self.key_prefix)
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

        # Always return valid state
        return state_data if state_data is not None else initial_state

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

            # Prepare and validate state update
            prepared_state = StateValidator.prepare_state_update(self, updates)

            # Merge updates with current state
            new_state = {**self._state, **prepared_state}

            # Persist to Redis first to ensure atomic update
            self.atomic_state.atomic_update(self.key_prefix, new_state)

            # Update local state only after successful Redis update
            self._state = new_state
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
                validation=self.get_validation_status("get")
            )

        # Track validation
        self._track_validation("get", "state_manager", None)
        return self._state.get(key)

    def get_validation_history(self) -> list:
        """Get validation history"""
        validation = self.get("validation") or {}
        return validation.get("history", [])

    def get_validation_status(self, operation: str) -> Dict[str, Any]:
        """Get validation status for operation

        Args:
            operation: Operation to get status for

        Returns:
            Dict with attempts count and latest history entry
        """
        validation = self.get("validation") or {}
        attempts = validation.get("attempts", {}).get(operation, 0)

        # Get latest history entry for operation
        history = validation.get("history", [])
        latest = next(
            (entry for entry in reversed(history) if entry["operation"] == operation),
            None
        )

        return {
            "attempts": attempts,
            "latest": latest
        }

    # Flow state methods

    # Protected state access
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard state (API-sourced)"""
        return self.get("dashboard") or {}

    def get_action_data(self) -> Dict[str, Any]:
        """Get action state (API-sourced)"""
        return self.get("action") or {}

    # Flow/Component state access
    def get_current_state(self) -> Dict[str, Any]:
        """Get current flow/component state"""
        return self.get("current") or {}

    def get_path(self) -> Optional[str]:
        """Get current flow path"""
        current = self.get_current_state()
        return current.get("path")

    def get_component(self) -> Optional[str]:
        """Get current component"""
        current = self.get_current_state()
        return current.get("component")

    def get_component_result(self) -> Optional[str]:
        """Get component result for flow branching"""
        current = self.get_current_state()
        return current.get("component_result")

    def get_component_data(self) -> Dict[str, Any]:
        """Get component-specific data"""
        current = self.get_current_state()
        return current.get("data", {})

    def is_awaiting_input(self) -> bool:
        """Check if component is waiting for input"""
        current = self.get_current_state()
        return current.get("awaiting_input", False)

    # State updates
    def update_current_state(
        self,
        path: str,
        component: str,
        data: Optional[Dict] = None,
        component_result: Optional[str] = None,
        awaiting_input: bool = False
    ) -> None:
        """Update current flow/component state with validation tracking

        Args:
            path: Current flow path
            component: Current component
            data: Optional component data
            component_result: Optional result for flow branching
            awaiting_input: Whether component is waiting for input

        Raises:
            Exception: If update fails (handled by ErrorHandler)
        """
        try:
            # Preserve existing component data if not provided
            if data is None:
                current = self.get_current_state()
                data = current.get("data", {})

            # Track validation
            self._track_validation("update_current", component)

            # Update state
            self.update_state({
                "current": {
                    "path": path,
                    "component": component,
                    "data": data,
                    "component_result": component_result,
                    "awaiting_input": awaiting_input
                }
            })

        except Exception as e:
            error_context = ErrorContext(
                error_type="flow",
                message=str(e),
                details={
                    "path": path,
                    "component": component,
                    "action": "update_current",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_error(e, self, error_context)

    def clear_current_state(self) -> None:
        """Clear current flow/component state"""
        self.update_state({"current": None})

    def clear_all_state(self) -> None:
        """Clear all state except protected core state"""
        try:
            # Preserve protected state
            channel = self.get("channel")
            dashboard = self.get("dashboard")
            action = self.get("action")
            auth = self.get("auth")

            # Reset to initial state
            self._state = {
                # Protected state
                "channel": channel,
                "dashboard": dashboard,
                "action": action,
                "auth": auth,

                # Reset metadata
                "_metadata": {
                    "initialized_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            }

            # Persist to Redis
            self.atomic_state.atomic_update(self.key_prefix, self._state)

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

    def _track_validation(self, operation: str, component: str, error: Optional[str] = None) -> None:
        """Track validation attempt in history

        Args:
            operation: Operation being validated
            component: Component performing validation
            error: Optional error message
        """
        validation = self.get("validation") or {"attempts": {}, "history": []}

        # Update attempts
        if operation not in validation["attempts"]:
            validation["attempts"][operation] = 0
        validation["attempts"][operation] += 1

        # Add to history
        validation["history"].append({
            "operation": operation,
            "component": component,
            "timestamp": datetime.utcnow().isoformat(),
            "success": error is None,
            "error": error
        })

        # Update state
        self.update_state({"validation": validation})

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token"""
        try:
            # Get auth data
            auth = self.get("auth") or {}
            dashboard = self.get_dashboard_data()
            jwt_token = auth.get("token")

            if not dashboard.get("member_id") or not jwt_token:
                return False

            # Validate token expiry locally
            from decouple import config
            from jwt import InvalidTokenError, decode
            try:
                decode(jwt_token, config("JWT_SECRET"), algorithms=["HS256"])
                return True
            except InvalidTokenError:
                return False

        except Exception:
            return False

    def get_member_id(self) -> Optional[str]:
        """Get member ID if authenticated"""
        if not self.is_authenticated():
            return None

        dashboard = self.get_dashboard_data()
        return dashboard.get("member_id")
