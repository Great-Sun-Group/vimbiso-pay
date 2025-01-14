"""Core state management interface

This module defines the interface for state management operations.
The interface uses composition to integrate messaging capabilities
while avoiding circular dependencies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.messaging.interface import MessagingServiceInterface


class StateManagerInterface(ABC):
    """Interface defining core state management operations"""

    @property
    @abstractmethod
    def messaging(self) -> MessagingServiceInterface:
        """Get messaging service

        Returns:
            MessagingServiceInterface: Messaging service implementation
        """
        pass

    @messaging.setter
    @abstractmethod
    def messaging(self, service: MessagingServiceInterface) -> None:
        """Set messaging service

        Args:
            service: Messaging service implementation
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with validation

        All updates are validated against the schema except for component_data.data
        which allows components to store arbitrary data.

        Args:
            updates: State updates to apply
        """
        pass

    @abstractmethod
    def get_path(self) -> Optional[str]:
        """Get current flow path"""
        pass

    @abstractmethod
    def get_component(self) -> Optional[str]:
        """Get current component"""
        pass

    @abstractmethod
    def get_component_result(self) -> Optional[str]:
        """Get component result for flow branching"""
        pass

    @abstractmethod
    def is_awaiting_input(self) -> bool:
        """Check if component is waiting for input"""
        pass

    @abstractmethod
    def transition_flow(self, path: str, component: str) -> None:
        """Transition flow to new path/component.
        ONLY used by flow processor for managing transitions.

        Args:
            path: New flow path
            component: New component
        """
        pass

    @abstractmethod
    def set_component_awaiting(self, awaiting: bool) -> None:
        """Set component's awaiting input state.
        Used by components to indicate they are waiting for input.

        Args:
            awaiting: Whether component is waiting for input
        """
        pass

    @abstractmethod
    def set_component_result(self, result: Optional[str]) -> None:
        """Set component result for flow branching.
        Used by components to indicate their result.

        Args:
            result: Optional result string for flow branching
        """
        pass

    @abstractmethod
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
        never use this directly - they should use Component.update_state() instead.

        Args:
            path: Current flow path (required)
            component: Current component (required)
            data: Optional component data
            component_result: Optional result for flow branching
            awaiting_input: Whether component is waiting for input
        """
        pass

    @abstractmethod
    def clear_component_data(self) -> None:
        """Clear flow/component state"""
        pass

    @abstractmethod
    def clear_all_state(self) -> None:
        """Clear all state data"""
        pass

    @abstractmethod
    def get_channel_id(self) -> str:
        """Get channel identifier

        Returns:
            Channel ID string
        """
        pass

    @abstractmethod
    def get_channel_type(self) -> str:
        """Get channel type

        Returns:
            Channel type string ("whatsapp" or "sms")
        """
        pass

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token

        Returns:
            bool: True if authenticated with valid token
        """
        pass

    @abstractmethod
    def get_member_id(self) -> Optional[str]:
        """Get member ID if authenticated

        Returns:
            Member ID string if authenticated with valid token
        """
        pass

    @abstractmethod
    def is_mock_testing(self) -> bool:
        """Check if mock testing mode is enabled for this request

        Returns:
            bool: True if mock testing mode is enabled
        """
        pass

    @abstractmethod
    def get_incoming_message(self) -> Optional[Dict[str, Any]]:
        """Get current incoming message if it exists

        Returns:
            Optional[Dict[str, Any]]: Message dict if exists, None otherwise
        """
        pass

    @abstractmethod
    def set_incoming_message(self, message: Dict[str, Any]) -> None:
        """Set the incoming message

        Args:
            message: Message dict conforming to incoming_message schema in component_data
        """
        pass

    @abstractmethod
    def initialize_channel(self, channel_type: str, channel_id: str, mock_testing: bool = False) -> None:
        """Initialize or update channel info - the only way to modify channel data

        Args:
            channel_type: Channel type string ("whatsapp" or "sms")
            channel_id: Channel identifier string
            mock_testing: Whether to enable mock testing mode

        Raises:
            ComponentException: If validation fails
        """
        pass
