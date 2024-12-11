from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class StateServiceInterface(ABC):
    """Abstract interface for state management operations"""

    @abstractmethod
    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Retrieve the current state for a user"""
        pass

    @abstractmethod
    def update_state(
        self,
        user_id: str,
        new_state: Dict[str, Any],
        stage: str,
        update_from: str,
        option: Optional[str] = None
    ) -> None:
        """Update the state for a user"""
        pass

    @abstractmethod
    def reset_state(self, user_id: str) -> None:
        """Reset the state for a user"""
        pass

    @abstractmethod
    def get_stage(self, user_id: str) -> str:
        """Get the current stage for a user"""
        pass

    @abstractmethod
    def set_stage(self, user_id: str, stage: str) -> None:
        """Set the current stage for a user"""
        pass

    @abstractmethod
    def get_option(self, user_id: str) -> Optional[str]:
        """Get the current option for a user"""
        pass

    @abstractmethod
    def set_option(self, user_id: str, option: str) -> None:
        """Set the current option for a user"""
        pass

    @abstractmethod
    def get_member_info(self, user_id: str) -> Dict[str, Any]:
        """Get member information for a user"""
        pass

    @abstractmethod
    def update_member_info(self, user_id: str, new_info: Dict[str, Any]) -> None:
        """Update member information for a user"""
        pass

    @abstractmethod
    def clear_member_info(self, user_id: str) -> None:
        """Clear member information for a user"""
        pass
