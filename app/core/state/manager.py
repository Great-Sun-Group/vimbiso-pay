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
from core.messaging.types import ChannelType
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
        # Start with empty initial state
        initial_state = {}

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
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )

        # Always return valid state
        return state_data if state_data is not None else initial_state

    def initialize_channel(self, channel_type: ChannelType, channel_id: str, mock_testing: bool = False) -> None:
        """Initialize or update channel info - the only way to modify channel data

        Args:
            channel_type: Channel type enum
            channel_id: Channel identifier string
            mock_testing: Whether to enable mock testing mode

        Raises:
            ComponentException: If validation fails
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Initializing channel - type: {channel_type} ({type(channel_type)}), id: {channel_id}, mock: {mock_testing}")

        # Convert enum to string for persistence
        channel_type_str = channel_type.value if isinstance(channel_type, ChannelType) else str(channel_type)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Channel type string: {channel_type_str} ({type(channel_type_str)})")

        # Construct updates with string channel type
        updates = {
            "channel": {
                "type": channel_type_str,
                "identifier": channel_id
            },
            "mock_testing": mock_testing
        }
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Channel updates: {updates}")

        # Validate updates
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Preparing state update for validation")
        prepared_state = StateValidator.prepare_state_update(updates)

        # Update state atomically
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Merging with existing state")
            logger.debug(f"Current state: {self._state}")
            logger.debug(f"Updates to apply: {prepared_state}")

        new_state = {**self._state, **prepared_state}
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"New merged state: {new_state}")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Performing atomic update")
        self.atomic_state.atomic_update(self.key_prefix, new_state)
        self._state = new_state

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with validation

        Args:
            updates: State updates to apply

        Raises:
            ComponentException: If updates format is invalid or attempts to modify channel
        """
        if not isinstance(updates, dict):
            raise ComponentException(
                message="Updates must be a dictionary",
                component="state_manager",
                field="updates",
                value=str(type(updates))
            )

        # Prevent channel modifications through normal updates
        if "channel" in updates:
            raise ComponentException(
                message="Channel can only be modified through initialize_channel",
                component="state_manager",
                field="channel",
                value=str(updates)
            )

        try:
            # Validate state update
            prepared_state = StateValidator.prepare_state_update(updates)

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
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )

    def _get(self, key: str) -> Any:
        """Internal method to get raw state value

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
                value=str(key)
            )

        return self._state.get(key)

    # State access - protection through schema validation, not access control
    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get any state value with default handling

        All state fields except component_data.data are protected by schema validation
        during updates, not by access control. Components have freedom to store any
        data in their component_data.data dict.

        Args:
            key: State key to get
            default: Default value if not found

        Returns:
            Value or default
        """
        try:
            value = self._get(key)
            return value if value is not None else default
        except Exception as e:
            # Handle error through ErrorHandler
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_GET_ERROR",
                    "service": "state_manager",
                    "action": "get_value",
                    "key": key,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )
            return default

    # Convenience methods for common state access
    def get_path(self) -> Optional[str]:
        """Get current flow path"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("path")

    def get_component(self) -> Optional[str]:
        """Get current component"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("component")

    def get_component_result(self) -> Optional[str]:
        """Get component result for flow branching"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("component_result")

    def is_awaiting_input(self) -> bool:
        """Check if component is waiting for input"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("awaiting_input", False)

    # Component state updates
    def update_flow_state(
        self,
        path: str,
        component: str,
        data: Optional[Dict] = None,
        component_result: Optional[str] = None,
        awaiting_input: bool = False
    ) -> None:
        """Update flow state including path and component

        This is the low-level interface used by the flow processor to manage transitions.
        It requires all schema fields including path and component. Components should
        never use this directly - they should use Component.update_component_data() instead.

        The component_data.data field is the only part of state not protected by
        schema validation, giving components freedom to store their own data.

        Args:
            path: Current flow path
            component: Current component
            data: Optional component data (unvalidated)
            component_result: Optional result for flow branching
            awaiting_input: Whether component is waiting for input

        Raises:
            Exception: If update fails (handled by ErrorHandler)
        """
        try:
            # Preserve existing component data if not provided
            if data is None:
                component_data = self.get_state_value("component_data", {})
                data = component_data.get("data", {})

            # Update state
            self.update_state({
                "component_data": {
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
            ErrorHandler.handle_flow_error(
                step=error_context.details["path"],
                action=error_context.details["action"],
                data={"component": error_context.details["component"]},
                message=error_context.message
            )

    def clear_component_data(self) -> None:
        """Clear component state including unvalidated data"""
        self.update_state({"component_data": None})

    def clear_all_state(self) -> None:
        """Clear all state data"""
        try:
            # Complete wipe of all state
            complete_state = {}

            # Update state and persist
            self._state = complete_state
            self.atomic_state.atomic_update(self.key_prefix, complete_state)

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
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )

    # Channel methods with required field validation

    def get_channel_id(self) -> str:
        """Get channel identifier

        Returns:
            Channel ID string

        Raises:
            ComponentException: If identifier not found in channel data
        """
        channel = self.get_state_value("channel", {})
        if not channel.get("identifier"):
            raise ComponentException(
                message="Channel identifier not found",
                component="state_manager",
                field="channel.identifier",
                value=str(channel)
            )
        return channel["identifier"]

    def get_channel_type(self) -> ChannelType:
        """Get channel type

        Returns:
            Channel type enum

        Raises:
            ComponentException: If type not found in channel data
        """
        channel_type = self.get_state_value("channel", {}).get("type")
        if not channel_type:
            raise ComponentException(
                message="Channel type not found",
                component="state_manager",
                field="channel.type"
            )
        return ChannelType(channel_type)

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token"""
        try:
            # Get auth data
            auth = self.get_state_value("auth", {})
            dashboard = self.get_state_value("dashboard", {})
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

        dashboard = self.get_state_value("dashboard", {})
        return dashboard.get("member_id")

    def is_mock_testing(self) -> bool:
        """Check if mock testing mode is enabled for this request"""
        return bool(self.get_state_value("mock_testing"))
