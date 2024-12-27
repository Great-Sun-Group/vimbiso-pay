"""WhatsApp message handling implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Tuple, Type

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...types import WhatsAppMessage
from ..credex.flows.action import AcceptFlow, CancelFlow, DeclineFlow
from ..credex.flows.offer import OfferFlow
from ..member.registration import RegistrationFlow
from ..member.upgrade import UpgradeFlow
from .flow_manager import FlowManager
from .flow_processor import FlowProcessor
from .input_handler import InputHandler

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MessageHandler:
    """Handler for WhatsApp messages with strict state management"""

    FLOW_TYPES: Dict[str, Tuple[str, Type]] = {
        "offer": ("offer", OfferFlow),
        "accept": ("accept", AcceptFlow),
        "decline": ("decline", DeclineFlow),
        "cancel": ("cancel", CancelFlow),
        "start_registration": ("registration", RegistrationFlow),
        "upgrade_tier": ("upgrade", UpgradeFlow)
    }

    def __init__(self, state_manager: Any):
        """Initialize with state manager

        Args:
            state_manager: State manager instance
        """
        if not state_manager:
            raise ValueError("State manager is required")
        self.state_manager = state_manager
        self.credex_service = state_manager.get_credex_service()
        self.auth_handler = None  # Will be set by auth handler

    def process_message(self, message_type: str, message_body: str) -> WhatsAppMessage:
        """Process incoming message enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "authenticated", "flow_data", "member_id"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Initial validation requires only channel
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Log message processing start
            audit.log_flow_event(
                "bot_service",
                "message_processing",
                None,
                {
                    "message_type": message_type,
                    "channel_id": channel["identifier"]
                },
                "in_progress"
            )

            # Initialize input handler
            input_handler = InputHandler(message_body)
            if not input_handler:
                raise ValueError("Failed to initialize input handler")

            # Get action from input
            action = input_handler.get_action()

            # Handle greeting
            if message_type == "text" and input_handler.is_greeting(message_body):
                # Validate state update
                new_flow_data = {
                    "flow_data": {
                        "id": "greeting",
                        "step": 0
                    }
                }
                validation = StateValidator.validate_state(new_flow_data)
                if not validation.is_valid:
                    raise ValueError(f"Invalid flow data: {validation.error_message}")

                # Update state
                success, error = self.state_manager.update_state(new_flow_data)
                if not success:
                    raise ValueError(f"Failed to update state: {error}")

                # Handle greeting
                return WhatsAppMessage.from_core_message(
                    self.auth_handler.handle_hi()
                )

            # Handle menu action
            if action in self.FLOW_TYPES:
                # Validate authentication state
                validation = StateValidator.validate_before_access(
                    current_state,
                    {"authenticated"}
                )
                if not validation.is_valid:
                    return WhatsAppMessage.from_core_message(
                        self.auth_handler.handle_menu(login=True)
                    )

                # Get flow type and class
                flow_type, flow_class = self.FLOW_TYPES[action]

                # Validate state update
                new_flow_data = {
                    "flow_data": {
                        "id": flow_type,
                        "step": 0
                    }
                }
                validation = StateValidator.validate_state(new_flow_data)
                if not validation.is_valid:
                    raise ValueError(f"Invalid flow data: {validation.error_message}")

                # Update state
                success, error = self.state_manager.update_state(new_flow_data)
                if not success:
                    raise ValueError(f"Failed to update state: {error}")

                # Initialize flow
                return WhatsAppMessage.from_core_message(
                    FlowManager.initialize_flow(
                        self.state_manager,
                        flow_type,
                        flow_class
                    )
                )

            # Handle active flow
            flow_data = self.state_manager.get("flow_data")
            if flow_data:
                # Validate flow data
                validation = StateValidator.validate_before_access(
                    {"flow_data": flow_data},
                    {"flow_data"}
                )
                if not validation.is_valid:
                    raise ValueError(f"Invalid flow data: {validation.error_message}")

                return FlowProcessor.process_flow(
                    self.state_manager,
                    input_handler,
                    flow_data
                )

            # Default to menu
            return WhatsAppMessage.from_core_message(
                self.auth_handler.handle_action_menu()
            )

        except ValueError as e:
            # Get channel info for error response
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error response: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Message processing error: {str(e)} for channel {channel_id}")
            return WhatsAppMessage.create_text(
                channel_id,
                "Error: Unable to process message. Please try again."
            )
