"""WhatsApp message handling implementation using component-based architecture"""
import logging
from typing import Any

from services.whatsapp.handlers.credex import (
    OfferFlow, AcceptFlow, DeclineFlow, CancelFlow
)
from services.whatsapp.handlers.member import RegistrationFlow, UpgradeFlow

from core.utils.flow_audit import FlowAuditLogger
from services.whatsapp.types import WhatsAppMessage
from .flow_manager import FlowManager
from .flow_processor import FlowProcessor
from .input_handler import InputHandler
from .state_handler import StateHandler

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class MessageHandler:
    """Handler for WhatsApp messages and flows"""

    FLOW_TYPES = {
        "offer_credex": ("offer", OfferFlow),
        "accept_credex": ("accept", AcceptFlow),
        "decline_credex": ("decline", DeclineFlow),
        "cancel_credex": ("cancel", CancelFlow),
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

            # Handle greeting
            if (self.service.message_type == "text" and
                    self.input_handler.is_greeting(self.service.body)):
                error = self.state_handler.prepare_flow_start(is_greeting=True)
                if error:
                    return error
                return self.service.auth_handler.handle_action_menu(login=True)

            # Check for active flow
            flow_data = self.state_handler.get_flow_data()
            if flow_data:
                # Handle greeting during active flow
                if (self.service.message_type == "text" and
                        self.input_handler.is_greeting(self.service.body)):
                    error = self.state_handler.prepare_flow_start(is_greeting=True)
                    if error:
                        return error
                    return self.service.auth_handler.handle_action_menu(login=True)
                return self.flow_processor.process_flow(flow_data)

            # Get action and check if it's a menu action
            action = self.input_handler.get_action()
            logger.info(f"Processing action: {action}")

            if action in self.FLOW_TYPES:
                error = self.state_handler.prepare_flow_start()
                if error:
                    return error

                # Start new flow
                flow_type, flow_class_name = self.FLOW_TYPES[action]
                return self.flow_manager.initialize_flow(flow_type, flow_class_name)

            # If no active flow and not a menu action, default to menu
            return self.service.auth_handler.handle_action_menu()

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "message_processing_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return self.state_handler.handle_error_state(str(e))
