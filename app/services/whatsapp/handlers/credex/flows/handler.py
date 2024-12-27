"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.state_validator import StateValidator

from .base import CredexFlow
from .dashboard_handler import CredexDashboardHandler
from .messages import (create_cancel_message, create_initial_prompt,
                       create_success_message)
from .steps import create_flow_steps

logger = logging.getLogger(__name__)


class CredexHandler(CredexFlow):
    """Handles credex operations with strict state management"""

    def __init__(self, state_manager: Any) -> None:
        """Initialize with state manager enforcing SINGLE SOURCE OF TRUTH

        Args:
            state_manager: State manager instance

        Raises:
            ValueError: If state validation fails or required data missing
        """
        if not state_manager:
            raise ValueError("State manager required")

        # Validate ALL required state at boundary
        required_fields = {"channel", "member_id", "authenticated", "flow_data"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Initial validation
        validation = StateValidator.validate_before_access(
            current_state,
            {"channel", "member_id"}  # Core requirements
        )
        if not validation.is_valid:
            raise ValueError(f"State validation failed: {validation.error_message}")

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Channel identifier not found")

        # Initialize base Flow class
        super().__init__(
            id="credex_flow",
            steps=create_flow_steps()
        )

        # Initialize services
        self.state_manager = state_manager
        self.credex_service = state_manager.get_or_create_credex_service()
        if not self.credex_service:
            raise ValueError("Failed to initialize credex service")

        self.dashboard = CredexDashboardHandler(state_manager)
        if not self.dashboard:
            raise ValueError("Failed to initialize dashboard handler")

        # Log initialization
        logger.info(f"Initialized CredexHandler for channel {channel['identifier']}")

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming message with strict state validation"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": self.state_manager.get("channel"),
                    "member_id": self.state_manager.get("member_id"),
                    "flow_data": self.state_manager.get("flow_data")
                },
                {"channel", "member_id", "flow_data"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            # Process message based on flow step
            flow_data = self.state_manager.get("flow_data")
            if not flow_data or "step" not in flow_data:
                return self._handle_initial_message()
            return self._handle_flow_message(message)

        except ValueError as e:
            logger.error(f"Message handling error: {str(e)}")
            channel = self.state_manager.get("channel")
            return create_cancel_message(
                channel["identifier"] if channel else "unknown",
                str(e)
            )

    def _handle_initial_message(self) -> Dict[str, Any]:
        """Handle first message enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Prepare new flow data
            new_state = {
                "flow_data": {
                    "id": "credex_flow",
                    "step": 0
                }
            }

            # Validate state update
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid flow data: {validation.error_message}")

            # Update state
            success, error = self.state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to update flow data: {error}")

            # Log success
            logger.info(f"Initialized credex flow for channel {channel['identifier']}")

            # Return initial prompt
            return create_initial_prompt(channel["identifier"])

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Initial message error: {str(e)} for channel {channel_id}")
            return create_cancel_message(channel_id, str(e))

    def _handle_flow_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message during flow enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not isinstance(message, dict):
                raise ValueError("Invalid message format")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Get and validate flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                raise ValueError("Invalid flow data format")

            # Get current step
            step = flow_data.get("step", 0)
            if not isinstance(step, int) or step >= len(self.steps):
                raise ValueError("Invalid step value")

            current_step = self.steps[step]
            if not current_step:
                raise ValueError("Step not found")

            # Validate input
            text = message.get("text", "").strip()
            if not text:
                raise ValueError("Empty message")

            if not current_step.validator(text):
                raise ValueError(f"Invalid {current_step.id} format")

            # Prepare new flow data
            new_flow_data = flow_data.copy()
            new_flow_data.update({
                f"input_{step}": text,
                "step": step + 1
            })

            # Validate state update
            new_state = {"flow_data": new_flow_data}
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid flow data: {validation.error_message}")

            # Update state
            success, error = self.state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to update flow data: {error}")

            # Log progress
            logger.info(f"Processed step {step} for channel {channel['identifier']}")

            # Get next step message or handle completion
            if step + 1 < len(self.steps):
                return self.steps[step + 1].get_message(self.state_manager)
            return self._handle_completion(message)

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Flow message error: {str(e)} for channel {channel_id}")
            return create_cancel_message(channel_id, str(e))

    def _handle_completion(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle flow completion enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not isinstance(message, dict):
                raise ValueError("Invalid message format")

            confirm = message.get("text", "").strip().lower()
            if confirm not in ["yes", "no"]:
                raise ValueError("Please reply with yes or no")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            if confirm == "yes":
                # Process the credex operation
                result = self.complete()
                if not result:
                    raise ValueError("Operation failed")

                # Update dashboard
                try:
                    self.dashboard.update(result)
                except ValueError as err:
                    logger.error(f"Dashboard update failed: {str(err)} for channel {channel['identifier']}")
                    raise ValueError(f"Failed to update dashboard: {str(err)}")

                # Prepare state update
                new_state = {"flow_data": None}
                validation = StateValidator.validate_state(new_state)
                if not validation.is_valid:
                    raise ValueError(f"Invalid state update: {validation.error_message}")

                # Clear flow data
                success, error = self.state_manager.update_state(new_state)
                if not success:
                    raise ValueError(f"Failed to clear flow data: {error}")

                # Log success
                logger.info(f"Successfully completed credex flow for channel {channel['identifier']}")

                # Return success message
                return create_success_message(channel["identifier"])

            # Prepare state update
            new_state = {"flow_data": None}
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid state update: {validation.error_message}")

            # Clear flow data
            success, error = self.state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to clear flow data: {error}")

            # Log cancellation
            logger.info(f"Cancelled credex flow for channel {channel['identifier']}")

            # Return cancel message
            return create_cancel_message(channel["identifier"])

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Completion error: {str(e)} for channel {channel_id}")
            return create_cancel_message(channel_id, str(e))
