"""Core message handling for credex flows"""
import logging
from typing import Any, Dict, Optional

from core.messaging.flow import Flow
from services.whatsapp.state_manager import StateManager

from .dashboard_handler import CredexDashboardHandler
from .messages import (create_cancel_message, create_error_message,
                       create_initial_prompt, create_success_message)
from .steps import create_flow_steps

logger = logging.getLogger(__name__)


class CredexHandler(Flow):
    """Handles credex operations with strict state management"""

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize with state manager"""
        if not state_manager:
            raise ValueError("State manager required")

        self._state_manager = state_manager
        self._dashboard = CredexDashboardHandler(state_manager)

        # Get current state
        state = state_manager.get_state()

        # Create flow ID from member ID
        flow_id = f"credex_{state.get('member_id', 'new')}"

        # Initialize base Flow class with steps
        super().__init__(
            id=flow_id,
            steps=create_flow_steps()
        )

    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming message"""
        try:
            # Get current state
            state = self._state_manager.get_state()
            channel_id = StateManager.get_channel_identifier(state)

            # Process message based on state
            if not state.get("flow_data"):
                return self._handle_initial_message()
            return self._handle_flow_message(message)

        except ValueError as e:
            # Return error message
            return create_error_message(channel_id, str(e))

    def _handle_initial_message(self) -> Dict[str, Any]:
        """Handle first message in flow"""
        # Get current state
        state = self._state_manager.get_state()
        channel_id = StateManager.get_channel_identifier(state)

        # Update state with new flow
        self._state_manager.update_state({
            "member_id": state.get("member_id"),  # SINGLE SOURCE OF TRUTH
            "channel": state.get("channel"),  # SINGLE SOURCE OF TRUTH
            "flow_data": {
                "step": 0,
                "data": {}
            }
        })

        # Return initial prompt
        return create_initial_prompt(channel_id)

    def _handle_flow_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message during flow"""
        # Get current state
        state = self._state_manager.get_state()
        channel_id = StateManager.get_channel_identifier(state)
        flow_data = state.get("flow_data", {})
        step = flow_data.get("step", 0)

        try:
            # Get current step
            current_step = self.steps[step]

            # Validate and transform input
            if not current_step.validator(message.get("text", "").strip()):
                raise ValueError(f"Invalid {current_step.id} format")

            # Transform input
            transformed = current_step.transformer(message.get("text", "").strip())

            # Update state
            new_flow_data = {
                "step": step + 1,
                "data": {
                    **flow_data.get("data", {}),
                    **transformed
                }
            }

            self._state_manager.update_state({
                "member_id": state.get("member_id"),  # SINGLE SOURCE OF TRUTH
                "channel": state.get("channel"),  # SINGLE SOURCE OF TRUTH
                "flow_data": new_flow_data
            })

            # Get next step message
            if step + 1 < len(self.steps):
                return self.steps[step + 1].message(channel_id)

            # Handle completion
            return self._handle_completion(message)

        except ValueError as e:
            return create_error_message(channel_id, str(e))

    def _handle_completion(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle flow completion"""
        # Get current state
        state = self._state_manager.get_state()
        channel_id = StateManager.get_channel_identifier(state)

        # Validate input
        confirm = message.get("text", "").strip().lower()
        if confirm not in ["yes", "no"]:
            raise ValueError("Please reply with yes or no")

        try:
            if confirm == "yes":
                # Process the credex operation
                result = self.complete()

                # Update dashboard
                self._dashboard.update_dashboard(result, self.id)

                # Clear flow data and return success
                self._state_manager.update_state({
                    "member_id": state.get("member_id"),  # SINGLE SOURCE OF TRUTH
                    "channel": state.get("channel"),  # SINGLE SOURCE OF TRUTH
                    "flow_data": None
                })

                return create_success_message(channel_id)
            else:
                # Clear flow data and return cancel
                self._state_manager.update_state({
                    "member_id": state.get("member_id"),  # SINGLE SOURCE OF TRUTH
                    "channel": state.get("channel"),  # SINGLE SOURCE OF TRUTH
                    "flow_data": None
                })

                return create_cancel_message(channel_id)

        except Exception as e:
            logger.error(f"Completion error: {str(e)}")
            return create_error_message(channel_id, str(e))
