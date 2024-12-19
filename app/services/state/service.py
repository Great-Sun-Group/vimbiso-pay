"""Simplified state service implementation"""
from typing import Any, Dict, Optional

from .data import StateData
from .exceptions import StateError
from .manager import StateManager


class StateService:
    """
    Simplified state service that provides atomic operations through StateManager
    while preserving critical fields through StateData.
    """

    def __init__(self, wa_id: Optional[str] = None):
        self._state_manager = StateManager()
        self._wa_id = wa_id

    def get(self, wa_id: Optional[str] = None) -> Dict[str, Any]:
        """Get state, using instance wa_id if none provided"""
        try:
            user_id = wa_id or self._wa_id
            if not user_id:
                return StateData.create_default()
            return self._state_manager.get(user_id)
        except Exception as e:
            raise StateError(f"Failed to get state: {str(e)}")

    def update(self, data: Dict[str, Any], wa_id: Optional[str] = None) -> None:
        """Update state while preserving critical fields"""
        try:
            user_id = wa_id or self._wa_id
            if not user_id:
                raise StateError("No WhatsApp ID provided")

            # Get current state and merge with new data
            current = self.get(user_id)
            merged = StateData.merge(current, data)

            # Update through manager
            self._state_manager.update(user_id, merged)
        except Exception as e:
            raise StateError(f"Failed to update state: {str(e)}")

    def clear(self, wa_id: Optional[str] = None) -> None:
        """Clear state while preserving critical fields"""
        try:
            user_id = wa_id or self._wa_id
            if not user_id:
                raise StateError("No WhatsApp ID provided")
            self._state_manager.clear(user_id)
        except Exception as e:
            raise StateError(f"Failed to clear state: {str(e)}")

    @property
    def jwt_token(self) -> Optional[str]:
        """Get JWT token from state"""
        try:
            if not self._wa_id:
                return None
            state = self.get()
            return state.get('jwt_token')
        except Exception as e:
            raise StateError(f"Failed to get JWT token: {str(e)}")

    def set_jwt_token(self, token: str, wa_id: Optional[str] = None) -> None:
        """Set JWT token in state"""
        try:
            user_id = wa_id or self._wa_id
            if not user_id:
                raise StateError("No WhatsApp ID provided")
            self.update({'jwt_token': token}, user_id)
        except Exception as e:
            raise StateError(f"Failed to set JWT token: {str(e)}")

    def clear_jwt_token(self, wa_id: Optional[str] = None) -> None:
        """Clear JWT token from state"""
        try:
            user_id = wa_id or self._wa_id
            if not user_id:
                raise StateError("No WhatsApp ID provided")
            self.update({'jwt_token': None}, user_id)
        except Exception as e:
            raise StateError(f"Failed to clear JWT token: {str(e)}")
