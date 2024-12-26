"""WhatsApp message handling implementation using component-based architecture"""
import logging
from typing import Any

from core.utils.flow_audit import FlowAuditLogger

from ...state_manager import StateManager
from ...types import WhatsAppMessage
from ..credex.flows import AcceptFlow, CancelFlow, DeclineFlow, OfferFlow
from ..member.registration import RegistrationFlow
from ..member.upgrade import UpgradeFlow
from .flow_manager import FlowManager
from .flow_processor import FlowProcessor
from .input_handler import InputHandler
from .state_handler import StateHandler

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MessageHandler:
    """Handler for WhatsApp messages and flows"""

    FLOW_TYPES = {
        "offer": ("offer", OfferFlow),
        "accept": ("accept", AcceptFlow),
        "decline": ("decline", DeclineFlow),
        "cancel": ("cancel", CancelFlow),
        "start_registration": ("registration", RegistrationFlow),
        "upgrade_tier": ("upgrade", UpgradeFlow)
    }

    def __init__(self, service: Any):
        """Initialize handler with service reference and components"""
        self.service = service
        self.input_handler = InputHandler(service)
        self.state_handler = StateHandler(service)
        self.flow_manager = FlowManager(service)
        self.flow_processor = FlowProcessor(service, self.input_handler, self.state_handler)

    def process_message(self) -> WhatsAppMessage:
        """Process incoming message"""
        try:
            # Log message processing start
            audit.log_flow_event(
                "bot_service",
                "message_processing",
                None,
                {
                    "message_type": self.service.message_type,
                    "body": self.service.body if self.service.message_type == "text" else None
                },
                "in_progress"
            )

            # Get action first
            action = self.input_handler.get_action()
            logger.info(f"Processing action: {action}")

            # Handle greeting
            if (self.service.message_type == "text" and
                    self.input_handler.is_greeting(self.service.body)):
                # Get channel identifier from service
                channel_id = self.service.user.channel_identifier

                # Log initial state for debugging
                logger.debug(f"Initial state: {self.service.user.state.state}")

                # Prepare state with channel info
                error = self.state_handler.prepare_flow_start(
                    is_greeting=True,
                    channel_identifier=channel_id
                )
                if error:
                    return WhatsAppMessage.from_core_message(error)

                # Log state after preparation
                logger.debug(f"State after prepare_flow_start: {self.service.user.state.state}")

                # Ensure channel info is set in state
                if not self.service.user.state.state.get("channel", {}).get("identifier"):
                    logger.error("Channel identifier missing after state preparation")
                    return WhatsAppMessage.create_text(
                        channel_id,
                        "❌ Error: Channel initialization failed"
                    )

                return WhatsAppMessage.from_core_message(self.service.auth_handler.handle_action_menu(login=True))

            # Check for menu action first
            if action in self.FLOW_TYPES:
                # Get flow type and class
                flow_type, flow_class = self.FLOW_TYPES[action]

                # Log flow initialization
                logger.info(f"Starting {flow_type} flow")
                logger.debug(f"Flow type: {flow_type}")
                logger.debug(f"Flow class: {flow_class.__name__}")

                # Get channel info from state
                state_data = self.service.user.state.state
                channel_id = StateManager.get_channel_identifier(state_data)

                # Prepare flow start with channel info only
                error = self.state_handler.prepare_flow_start(
                    flow_type=flow_type,
                    channel_identifier=channel_id
                )
                if error:
                    logger.error(f"Failed to prepare flow state: {error}")
                    return WhatsAppMessage.from_core_message(error)

                # Initialize flow with channel info only
                result = self.flow_manager.initialize_flow(
                    flow_type=flow_type,
                    flow_class=flow_class,
                    kwargs={
                        "channel": {
                            "type": StateManager.get_channel_type(state_data),
                            "identifier": channel_id
                        }
                    }
                )
                logger.info(f"Flow {flow_type} initialized")
                return WhatsAppMessage.from_core_message(result)

            # Check for active flow if not a menu action
            flow_data = self.state_handler.get_flow_data()
            if flow_data:
                return self.flow_processor.process_flow(flow_data)

            # If no active flow and not a menu action, default to menu
            return WhatsAppMessage.from_core_message(self.service.auth_handler.handle_action_menu())

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "message_processing_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return WhatsAppMessage.from_core_message(self.state_handler.handle_error_state(str(e)))
