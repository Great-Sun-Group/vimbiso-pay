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
from typing import Any, Dict

from core import components
from core.messaging.types import Message, TextContent
from core.utils.error_handler import ErrorHandler
from services.messaging.service import MessagingService
from core.messaging.utils import get_recipient

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

    def process_message(self, payload: Dict[str, Any], state_manager: Any) -> Message:
        """Process message through flow framework

        Args:
            payload: Raw message payload
            state_manager: State manager instance

        Returns:
            Message: Response message
        """
        try:
            # Extract message data
            message_data = self._extract_message_data(payload)

            # Extract message content and update state
            message_type = message_data.get("type", "")
            message_text = message_data.get("text", {}).get("body", "") if message_type == "text" else ""

            # Update state with message data (SINGLE SOURCE OF TRUTH)
            state_manager.update_state({
                "message": {
                    "type": message_type,
                    "text": message_text,
                    "_metadata": {
                        "received_at": (state_manager.get("_metadata") or {}).get("updated_at")
                    }
                }
            })

            # Create message recipient
            recipient = get_recipient(state_manager)

            # Get current flow state or initialize new flow
            flow_state = state_manager.get("flow_data") or {}
            context = flow_state.get("context", "login")
            component = flow_state.get("component", "Greeting")

            # Process through flow framework
            from core.messaging.flow import process_component
            result, next_context, next_component = process_component(
                context=context,
                component=component,
                state_manager=state_manager
            )

            # Update flow state
            state_manager.update_state({
                "flow_data": {
                    "context": next_context,
                    "component": next_component,
                    "result": result
                }
            })

            # Get component class to convert result to message
            component_class = getattr(components, component)
            component_instance = component_class()
            component_instance.state_manager = state_manager

            # Handle ValidationResult objects
            if hasattr(result, "valid"):
                if not result.valid and result.error:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=result.error.get("message", "Validation failed")
                    )
                result = result.value

            # Convert result to message content
            try:
                message_content = component_instance.to_message_content(result)
                return self.messaging.send_text(
                    recipient=recipient,
                    text=message_content
                )
            except (AttributeError, KeyError) as e:
                logger.error(f"Error converting component result to message: {str(e)}")
                # Fallback to raw result if conversion fails
                if isinstance(result, dict) and "message" in result:
                    return self.messaging.send_text(
                        recipient=recipient,
                        text=result["message"]
                    )
                return self.messaging.send_text(
                    recipient=recipient,
                    text="Processing your request..."
                )

        except Exception as e:
            # Handle system errors
            error_response = ErrorHandler.handle_system_error(
                code="FLOW_ERROR",
                service="flow_processor",
                action="process_message",
                message=str(e),
                error=e
            )

            recipient = get_recipient(state_manager)
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
