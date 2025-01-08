"""Flow processor for handling message flows through components.

This module handles the complete flow processing lifecycle:
1. Takes channel input and prepares for flow
2. Manages flow state
3. Processes through components
4. Converts results to messages

The flow processor is channel-agnostic and works with any messaging service
that implements the MessagingServiceInterface.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from core.config.recognition import GREETING_COMMANDS
from core.messaging.types import Message, TextContent
from core.messaging.utils import get_recipient
from core.utils.error_handler import ErrorHandler
from core.utils.error_types import ValidationResult
from core.utils.exceptions import ComponentException
from services.messaging.service import MessagingService

logger = logging.getLogger(__name__)


class FlowProcessor:
    """Processes messages through the flow framework"""

    def __init__(self, messaging_service: MessagingService, state_manager: Any):
        """Initialize with messaging service and state manager

        Args:
            messaging_service: Channel-agnostic messaging service
            state_manager: State manager instance
        """
        self.messaging = messaging_service
        self.state_manager = state_manager
        # Ensure bidirectional relationship is set up
        if not hasattr(state_manager, 'messaging') or state_manager.messaging is None:
            state_manager.messaging = messaging_service

    def process_message(self, payload: Dict[str, Any]) -> Message:
        """Process message through flow framework

        Args:
            payload: Raw message payload

        Returns:
            Message: Response message
        """
        try:
            # Extract message data
            message_data = self._extract_message_data(payload)

            # Extract message content and update state
            message_type = message_data.get("type", "")
            message_text = message_data.get("text", {}).get("body", "") if message_type == "text" else ""

            # Create message recipient
            recipient = get_recipient(self.state_manager)

            # Check if message is a greeting
            current_component = self.state_manager.get_component()
            if (message_type == "text" and
                message_text.lower().strip() in GREETING_COMMANDS and
                    (not current_component or not current_component.lower().endswith('input'))):
                # Wipe state and set login flow
                self.state_manager.clear_all_state()
                self.state_manager.update_flow_state(
                    context="login",
                    component="Greeting"
                )

            # Get current flow state or initialize new flow
            flow_state = self.state_manager.get("flow_data")
            if not flow_state:
                # Initialize new flow with message data
                flow_state = {
                    "context": "login",
                    "component": "Greeting",
                    "data": {
                        "message": {
                            "type": message_type,
                            "text": message_text,
                            "_metadata": {
                                "received_at": datetime.utcnow().isoformat()
                            }
                        }
                    },
                    "_metadata": {
                        "initialized_at": datetime.utcnow().isoformat()
                    }
                }
            else:
                # Update existing flow with message data
                flow_state["data"] = flow_state.get("data", {})
                flow_state["data"]["message"] = {
                    "type": message_type,
                    "text": message_text,
                    "_metadata": {
                        "received_at": datetime.utcnow().isoformat()
                    }
                }

            # Update flow state
            self.state_manager.update_state({"flow_data": flow_state})

            context = flow_state.get("context", "login")
            component = flow_state.get("component", "Greeting")

            # Process through flow framework
            from core.messaging.flow import (activate_component,
                                             handle_component_result)
            logger.info(f"Processing flow: {context} -> {component}")

            # Log state before processing
            logger.info(f"Flow state before processing: {flow_state}")

            # Process component and get next step
            logger.info(f"Activating component: {component}")
            result = activate_component(component, self.state_manager)
            logger.info(f"Component result: {result}")

            # Get next component
            logger.info(f"Handling component result for {context}.{component}")
            next_step = handle_component_result(
                context=context,
                component=component,
                result=result,
                state_manager=self.state_manager
            )
            logger.info(f"Got next step: {next_step}")

            if next_step is None:
                logger.error(f"handle_component_result returned None for {context}.{component}")
                # Default to staying on current component
                next_context, next_component = context, component
            else:
                next_context, next_component = next_step

            logger.info(f"Flow transition: {context}.{component} -> {next_context}.{next_component}")

            # Update flow state with just context and component
            self.state_manager.update_flow_state(
                context=next_context,
                component=next_component
            )
            logger.info(f"Updated flow state: {next_context}.{next_component}")

            # Only return messages for errors, components handle their own messaging
            if isinstance(result, ValidationResult):
                if not result.valid:
                    # Component returned an error
                    content = TextContent(body=result.error.get("message", "Validation failed"))
                    return Message(recipient=recipient, content=content)
                # Component succeeded
                return None
            # Non-ValidationResult returns also succeed silently
            return None

        except ComponentException as e:
            # Handle component errors with validation state
            error_response = ErrorHandler.handle_component_error(
                component=e.details["component"],
                field=e.details["field"],
                value=e.details["value"],
                message=str(e),
                validation_state=e.details.get("validation")
            )
            recipient = get_recipient(self.state_manager)
            content = TextContent(body=error_response["error"]["message"])
            return Message(recipient=recipient, content=content)

        except Exception as e:
            # Handle system errors
            error_response = ErrorHandler.handle_system_error(
                code="FLOW_ERROR",
                service="flow_processor",
                action="process_message",
                message=str(e),
                error=e
            )
            recipient = get_recipient(self.state_manager)
            content = TextContent(body=error_response["error"]["message"])
            return Message(recipient=recipient, content=content)

    def _extract_message_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message data from payload

        This method should be overridden by channel-specific processors
        to handle channel-specific payload formats.

        Args:
            payload: Raw message payload

        Returns:
            Dict[str, Any]: Extracted message data

        Raises:
            ComponentException: If payload is invalid
        """
        raise NotImplementedError("Channel-specific processors must implement _extract_message_data")
