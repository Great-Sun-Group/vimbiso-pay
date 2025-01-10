"""Flow processor for handling message flows through components.

This module handles the complete flow processing lifecycle:
1. Takes channel input and prepares for flow
2. Manages state through schema validation
3. Processes through components (which can store unvalidated data)
4. Converts results to messages

The flow processor is channel-agnostic and works with any messaging service
that implements the MessagingServiceInterface. All state updates are protected
by schema validation except for component_data.data which gives components
freedom to store their own data.
"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.error.handler import ErrorHandler
from core.error.types import ValidationResult
from core.messaging.messages import INVALID_ACTION
from core.messaging.service import MessagingService
from core.messaging.types import Message, TextContent
from core.messaging.utils import get_recipient
from core.state.interface import StateManagerInterface

from .constants import GREETING_COMMANDS
from .headquarters import process_component

logger = logging.getLogger(__name__)


class FlowProcessor:
    """Processes messages through the flow framework"""

    def __init__(self, messaging_service: MessagingService, state_manager: StateManagerInterface):
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

            # Skip processing if no valid message data
            if not message_data:
                logger.debug("No valid message data to process")
                return None

            # Create message recipient for error handling
            recipient = get_recipient(self.state_manager)

            # Get message type and text
            message_type = message_data.get("type", "")
            message_text = message_data.get("text", {}).get("body", "").lower().strip()

            # Only process if we have valid text
            if not message_text:
                logger.debug("No valid message text to process")
                return None

            # Get current flow state (component_data is schema validated except for data dict)
            current_state = self.state_manager.get_state_value("component_data")

            # If no state, only accept greetings
            if not current_state:
                if message_type == "text" and message_text in GREETING_COMMANDS:
                    # Start login flow
                    self.state_manager.clear_all_state()
                    self.state_manager.update_component_data(
                        path="login",
                        component="Greeting"
                    )
                    current_state = self.state_manager.get_state_value("component_data")
                else:
                    # No state and not a greeting - send invalid action message
                    logger.debug("No state found - sending invalid action message")
                    self.messaging.send_text(
                        recipient=recipient,
                        text=INVALID_ACTION
                    )
                    return None

            context = current_state.get("path")
            component = current_state.get("component")

            # Process components until awaiting input or failure
            while True:
                logger.info(f"Processing component: {context}.{component}")
                logger.info(f"Current state: {current_state}")
                logger.info(f"Awaiting input: {self.state_manager.is_awaiting_input()}")

                # Process current component
                next_step = process_component(context, component, self.state_manager, depth=0)
                result = self.state_manager.get_component_result()

                logger.info(f"Component processing complete. Next step: {next_step}")
                logger.info(f"Component result: {result}")
                logger.info(f"Awaiting input: {self.state_manager.is_awaiting_input()}")

                # Handle component failure
                if next_step is None:
                    logger.error(f"Component failed: {context}.{component}")
                    return None

                # Handle validation error
                if isinstance(result, ValidationResult) and not result.valid:
                    content = TextContent(body=result.error.get("message", "Validation failed"))
                    return Message(recipient=recipient, content=content)

                # Get next step
                next_context, next_component = next_step
                if next_context != context or next_component != component:
                    # Log state transition
                    logger.info(f"Flow transition: {context}.{component} -> {next_context}.{next_component}")

                    # Update flow state
                    current_data = self.state_manager.get_state_value("component_data")
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Updating flow state: {current_data}")

                    self.state_manager.update_component_data(
                        path=next_context,
                        component=next_component,
                        data=current_data
                    )

                    # Return if awaiting input
                    if self.state_manager.is_awaiting_input():
                        logger.info("Awaiting input - returning from process_message")
                        return None

                    # Update for next iteration
                    context = next_context
                    component = next_component
                    current_state = self.state_manager.get_state_value("component_data")
                else:
                    # No state change - return
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