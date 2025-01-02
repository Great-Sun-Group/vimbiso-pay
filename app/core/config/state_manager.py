"""State management with clear boundaries

This module provides state management with:
- Single source of truth
- Clear boundaries
- Simple validation
- Minimal nesting
"""

import logging
from typing import Any, Dict, Optional

from core.utils.exceptions import StateException
from .atomic_state import AtomicStateManager
from .state_utils import (clear_flow_state, update_flow_data, update_flow_state,
                          update_state_core)
from django.core.cache import cache

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state with clear boundaries"""

    def __init__(self, key_prefix: str):
        """Initialize state manager

        Args:
            key_prefix: Redis key prefix (must start with 'channel:')

        Raises:
            StateException: If key prefix invalid
        """
        if not key_prefix or not key_prefix.startswith("channel:"):
            raise StateException("Invalid key prefix - must start with 'channel:'")

        self.key_prefix = key_prefix
        self.atomic_state = AtomicStateManager(cache)
        self._state = self._initialize_state()

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state structure"""
        # Get channel ID from prefix
        channel_id = self.key_prefix.split(":", 1)[1]

        # Create initial state
        initial_state = {
            "channel": {
                "type": "whatsapp",
                "identifier": channel_id
            }
        }

        # Get existing state
        state_data, error = self.atomic_state.atomic_get(self.key_prefix)
        if error:
            raise StateException(f"Failed to get state: {error}")

        # Use existing or initial state
        return state_data or initial_state

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with validation

        Args:
            updates: State updates to apply

        Raises:
            StateException: If update invalid or fails
        """
        if not isinstance(updates, dict):
            raise StateException("Updates must be a dictionary")

        success, error = update_state_core(self, updates)
        if not success:
            raise StateException(f"Failed to update state: {error}")

    def get(self, key: str) -> Any:
        """Get state value

        Args:
            key: State key to get

        Returns:
            Value for key or None

        Raises:
            StateException: If key invalid
        """
        if not key or not isinstance(key, str):
            raise StateException("Key must be a non-empty string")
        return self._state.get(key)

    # Flow state methods

    def get_flow_state(self) -> Optional[Dict[str, Any]]:
        """Get current flow state"""
        return self.get("flow_data")

    def get_flow_type(self) -> Optional[str]:
        """Get current flow type"""
        flow_data = self.get_flow_state()
        return flow_data.get("flow_type") if flow_data else None

    def get_flow_step(self) -> Optional[str]:
        """Get current flow step"""
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
        """Update flow state

        Args:
            flow_type: Type of flow
            step: Current step
            data: Optional flow data

        Raises:
            StateException: If update fails
        """
        success, error = update_flow_state(self, flow_type, step, data)
        if not success:
            raise StateException(f"Failed to update flow state: {error}")

    def update_flow_data(self, data: Dict[str, Any]) -> None:
        """Update flow data

        Args:
            data: Flow data updates

        Raises:
            StateException: If update fails
        """
        success, error = update_flow_data(self, data)
        if not success:
            raise StateException(f"Failed to update flow data: {error}")

    def clear_flow_state(self) -> None:
        """Clear flow state

        Raises:
            StateException: If clear fails
        """
        success, error = clear_flow_state(self)
        if not success:
            raise StateException(f"Failed to clear flow state: {error}")

    # Channel methods

    def get_channel_id(self) -> str:
        """Get channel identifier

        Returns:
            Channel ID string

        Raises:
            StateException: If channel ID not found
        """
        channel = self.get("channel")
        if not channel or not channel.get("identifier"):
            raise StateException("Channel identifier not found")
        return channel["identifier"]

    def get_channel_type(self) -> str:
        """Get channel type

        Returns:
            Channel type string

        Raises:
            StateException: If channel type not found
        """
        channel = self.get("channel")
        if not channel or not channel.get("type"):
            raise StateException("Channel type not found")
        return channel["type"]
