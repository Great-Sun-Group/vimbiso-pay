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
    def get_flow_state(self) -> Optional[Dict[str, Any]]:
        """Get current flow state"""
        pass

    @abstractmethod
    def get_context(self) -> Optional[str]:
        """Get current context"""
        pass

    @abstractmethod
    def get_component(self) -> Optional[str]:
        """Get current component"""
        pass

    @abstractmethod
    def get_flow_data(self) -> Dict[str, Any]:
        """Get current flow data"""
        pass

    @abstractmethod
    def update_flow_state(
        self,
        context: str,
        component: str,
        data: Optional[Dict] = None
    ) -> None:
        """Update flow state with validation

        Args:
            context: Current context
            component: Current component
            data: Optional flow data
        """
        pass

    @abstractmethod
    def update_flow_data(self, data: Dict[str, Any]) -> None:
        """Update flow data

        Args:
            data: Flow data updates
        """
        pass

    @abstractmethod
    def clear_flow_state(self) -> None:
        """Clear flow state"""
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
