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

from core.messaging.interface import MessagingServiceInterface
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ErrorContext
from core.utils.exceptions import ComponentException
from core.utils.redis_client import get_redis_client

from .atomic_state import AtomicStateManager
from .interface import StateManagerInterface
from .state_utils import prepare_state_update

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
            prepared_state = prepare_state_update(self, updates)

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

    def get_context(self) -> Optional[str]:
        """Get current context"""
        flow_data = self.get_flow_state()
        return flow_data.get("context") if flow_data else None

    def get_component(self) -> Optional[str]:
        """Get current component"""
        flow_data = self.get_flow_state()
        return flow_data.get("component") if flow_data else None

    def get_flow_data(self) -> Dict[str, Any]:
        """Get current flow data"""
        flow_data = self.get_flow_state()
        return flow_data.get("data", {}) if flow_data else {}

    def update_flow_state(
        self,
        context: str,
        component: str,
        data: Optional[Dict] = None
    ) -> None:
        """Update flow state with validation tracking

        Args:
            context: Current context
            component: Current component
            data: Optional flow data

        Raises:
            Exception: If flow state update fails (handled by ErrorHandler)
        """
        # Get current flow state for validation tracking
        current_flow = self.get_flow_state() or {}

        # Track validation attempt
        validation_state = {
            "in_progress": True,
            "attempts": current_flow.get("validation_attempts", 0) + 1,
            "last_attempt": {
                "context": context,
                "component": component,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        try:
            # Get current flow data to preserve
            current_flow = self.get_flow_state() or {}
            current_data = current_flow.get("data", {})

            # Merge new data with existing data
            merged_data = {
                **current_data,  # Preserve existing data
                **(data or {})   # Add new data
            }

            # Prepare and apply flow state update
            self.update_state({
                "flow_data": {
                    "context": context,
                    "component": component,
                    "data": merged_data,
                    "validation": validation_state,
                    "_metadata": {
                        "updated_at": datetime.utcnow().isoformat()
                    }
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
                    "context": context,
                    "component": component,
                    "action": "update_state",
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
        # Prepare and apply flow data update
        self.update_state({
            "flow_data": {
                "data": data
            }
        })

    def clear_flow_state(self) -> None:
        """Clear flow state

        Raises:
            Exception: If flow state clear fails (handled by ErrorHandler)
        """
        # Clear flow state
        self.update_state({
            "flow_data": None
        })

    def clear_all_state(self) -> None:
        """Clear all state data except channel info

        Resets state to initial with just channel info.
        Clears all other data including flow state, validation state, metadata, etc.

        Raises:
            Exception: If state clear fails (handled by ErrorHandler)
        """
        try:
            # Get state info to preserve
            channel = self.get("channel")
            mock_testing = self.get("mock_testing")

            # Reset to initial state with preserved values
            self._state = {
                "channel": channel,
                "mock_testing": mock_testing,  # Always preserve mock flag even if None
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

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token

        Returns:
            bool: True if authenticated with valid token, False otherwise
        """
        try:
            # Get auth data from flow state
            flow_data = self.get_flow_state() or {}
            dashboard = flow_data.get("data", {}).get("dashboard", {})
            jwt_token = flow_data.get("data", {}).get("auth", {}).get("token")

            if not dashboard.get("member_id") or not jwt_token:
                return False

            # Validate token expiry locally
            from decouple import config
            from jwt import InvalidTokenError, decode
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
        # Get member_id from dashboard data if authenticated
        if not self.is_authenticated():
            return None

        flow_data = self.get_flow_state() or {}
        dashboard = flow_data.get("data", {}).get("dashboard", {})
        return dashboard.get("member_id")
