"""State management with clear boundaries

This module provides state management with:
- Single source of truth
- Clear boundaries
- Simple validation
- Minimal nesting
"""

import logging
from typing import Any, Dict, Optional

from core.utils.exceptions import (ComponentException, FlowException,
                                   SystemException)
from django.core.cache import cache

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
        try:
            state_data = self.atomic_state.atomic_get(self.key_prefix)
        except SystemException as e:
            # Re-raise with initialization context
            raise SystemException(
                message=str(e),
                code="STATE_INIT_ERROR",
                service="state_manager",
                action="initialize"
            )

        # Use existing or initial state
        return state_data or initial_state

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with validation

        Args:
            updates: State updates to apply

        Raises:
            ComponentException: If updates format is invalid
            SystemException: If state update fails
        """
        if not isinstance(updates, dict):
            raise ComponentException(
                message="Updates must be a dictionary",
                component="state_manager",
                field="updates",
                value=str(type(updates))
            )

        try:
            update_state_core(self, updates)
        except SystemException as e:
            # Re-raise with update context
            raise SystemException(
                message=str(e),
                code="STATE_UPDATE_ERROR",
                service="state_manager",
                action="update"
            )

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
                    "last_attempt": key
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
            FlowException: If flow state update fails
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
                "data": data
            }
        }

        try:
            success, error = update_flow_state(self, flow_type, step, {
                **(data or {}),
                "step_index": current_step_index + 1,
                "total_steps": total_steps,
                "validation": validation_state
            })

            if not success:
                validation_state.update({
                    "in_progress": False,
                    "error": error
                })
                raise FlowException(
                    message=f"Failed to update flow state: {error}",
                    step=step,
                    action="update_state",
                    data={
                        "flow_type": flow_type,
                        "validation": validation_state
                    }
                )

            # Update validation state on success
            validation_state.update({
                "in_progress": False,
                "error": None
            })

        except Exception as e:
            validation_state.update({
                "in_progress": False,
                "error": str(e)
            })
            raise FlowException(
                message=str(e),
                step=step,
                action="update_state",
                data={
                    "flow_type": flow_type,
                    "validation": validation_state
                }
            )

    def update_flow_data(self, data: Dict[str, Any]) -> None:
        """Update flow data

        Args:
            data: Flow data updates

        Raises:
            FlowException: If flow data update fails
        """
        success, error = update_flow_data(self, data)
        if not success:
            raise FlowException(
                message=f"Failed to update flow data: {error}",
                step="update_data",
                action="update",
                data=data
            )

    def clear_flow_state(self) -> None:
        """Clear flow state

        Raises:
            FlowException: If flow state clear fails
        """
        success, error = clear_flow_state(self)
        if not success:
            raise FlowException(
                message=f"Failed to clear flow state: {error}",
                step="clear",
                action="clear_state",
                data={}
            )

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

    def get_member_id(self) -> Optional[str]:
        """Get member ID from flow data

        Returns:
            Member ID string if authenticated, None otherwise

        Raises:
            ComponentException: If flow data access fails
        """
        try:
            flow_data = self.get_flow_data()
            auth_data = flow_data.get("auth", {})

            if auth_data.get("authenticated"):
                member_id = auth_data.get("member_id")
                if not member_id:
                    raise ComponentException(
                        message="Member ID not found in authenticated state",
                        component="state_manager",
                        field="auth.member_id",
                        value=str(auth_data)
                    )
                return member_id
            return None

        except Exception as e:
            raise ComponentException(
                message=f"Failed to get member ID: {str(e)}",
                component="state_manager",
                field="member_id",
                value="None"
            )
