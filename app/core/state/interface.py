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
    def get(self, key: str) -> Any:
        """Get state value

        Args:
            key: State key

        Returns:
            Value for key or None
        """
        pass

    @abstractmethod
    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with validation

        Args:
            updates: State updates to apply
        """
        pass

    @abstractmethod
    def get_current_state(self) -> Dict[str, Any]:
        """Get current flow/component state"""
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
    def get_component_data(self) -> Dict[str, Any]:
        """Get component-specific data"""
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
    def update_current_state(
        self,
        path: str,
        component: str,
        data: Optional[Dict] = None,
        component_result: Optional[str] = None,
        awaiting_input: bool = False
    ) -> None:
        """Update current flow/component state

        Args:
            path: Current flow path
            component: Current component
            data: Optional component data
            component_result: Optional result for flow branching
            awaiting_input: Whether component is waiting for input
        """
        pass

    @abstractmethod
    def clear_current_state(self) -> None:
        """Clear current flow/component state"""
        pass

    @abstractmethod
    def get_validation_history(self) -> list:
        """Get validation history"""
        pass

    @abstractmethod
    def get_validation_status(self, operation: str) -> Dict[str, Any]:
        """Get validation status for operation

        Args:
            operation: Operation to get status for

        Returns:
            Dict with attempts count and latest history entry
        """
        pass

    @abstractmethod
    def clear_all_state(self) -> None:
        """Clear all state data except channel info"""
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
            Channel type string
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
