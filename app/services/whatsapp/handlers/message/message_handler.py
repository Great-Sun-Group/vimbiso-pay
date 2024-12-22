"""WhatsApp message handling implementation using component-based architecture"""
import logging
from typing import Any

from core.utils.flow_audit import FlowAuditLogger

from ...types import WhatsAppMessage
from ..credex.flows import (
    OfferFlow, AcceptFlow, DeclineFlow, CancelFlow
)
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
                error = self.state_handler.prepare_flow_start(is_greeting=True)
                if error:
                    return error
                return self.service.auth_handler.handle_action_menu(login=True)

            # Check for menu action first
            if action in self.FLOW_TYPES:
                # Get flow type and class
                flow_type, flow_class = self.FLOW_TYPES[action]

                # Log flow initialization
                logger.info(f"Starting {flow_type} flow")
                logger.debug(f"Flow type: {flow_type}")
                logger.debug(f"Flow class: {flow_class.__name__}")

                # Prepare state with flow type
                error = self.state_handler.prepare_flow_start(flow_type=flow_type)
                if error:
                    logger.error(f"Failed to prepare flow state: {error}")
                    return error

                # Get prepared flow data
                flow_data = self.state_handler.get_flow_data()
                if not flow_data:
                    logger.error("No flow data available after preparation")
                    return WhatsAppMessage.create_text(
                        self.service.user.mobile_number,
                        "❌ Error: Flow initialization failed"
                    )

                # Initialize flow with prepared flow data
                result = self.flow_manager.initialize_flow(
                    flow_type=flow_type,
                    flow_class=flow_class,
                    flow_data=flow_data,
                    kwargs={}
                )
                logger.info(f"Flow {flow_type} initialized")
                return result

            # Check for active flow if not a menu action
            flow_data = self.state_handler.get_flow_data()
            if flow_data:
                return self.flow_processor.process_flow(flow_data)

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
