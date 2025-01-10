"""WhatsApp-specific flow processor implementation"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.flow.processor import FlowProcessor
from core.messaging.types import (
    ChannelType,
    InteractiveType,
    MessageType,
)

logger = logging.getLogger(__name__)


class WhatsAppFlowProcessor(FlowProcessor):
    """WhatsApp implementation of flow processor"""

    def _extract_message_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message data from WhatsApp payload

        Args:
            payload: WhatsApp message payload

        Returns:
            Dict[str, Any]: Extracted message data

        Raises:
            ComponentException: If payload is invalid
        """
        if not payload:
            raise ComponentException(
                message="Message payload is required",
                component="whatsapp_flow_processor",
                field="payload",
                value=str(payload)
            )

        try:
            # Extract and validate each level
            entry = payload.get("entry", [])
            if not entry:
                raise ValueError("Missing entry array")

            changes = entry[0].get("changes", [])
            if not changes:
                raise ValueError("Missing changes array")

            value = changes[0].get("value", {})
            if not value:
                raise ValueError("Missing value object")

            # Check if this is a status update
            if "statuses" in value:
                logger.debug("Received status update - skipping processing")
                return {}

            # Check for messages
            messages = value.get("messages", [])
            if not messages:
                logger.debug("No messages to process")
                return {}

            message = messages[0]
            if not message:
                logger.debug("Empty message object")
                return {}

            # Only process user-initiated messages
            if not message.get("from"):
                logger.debug("Skipping non-user message")
                return {}

            # Get channel info from payload
            if not value.get("messaging_product") == "whatsapp":
                raise ValueError("Missing or invalid messaging product")

            # Get contact info
            contacts = value.get("contacts", [])
            if not contacts:
                raise ValueError("Missing contacts array")

            contact = contacts[0]
            if not contact or not isinstance(contact, dict):
                raise ValueError("Invalid contact object")

            channel_id = contact.get("wa_id")
            if not channel_id:
                raise ValueError("Missing WhatsApp ID")

            # Create base message data
            mock_testing = bool(value.get("metadata", {}).get("mock_testing", False))
            base_data = {
                "channel_type": ChannelType.WHATSAPP.value,  # Store enum value as string
                "channel_id": channel_id,
                "mock_testing": mock_testing
            }

            message_type = message.get("type")
            if message_type == "text":
                # Handle text messages
                message_data = message.copy()
                message_data.update(base_data)
                return message_data

            elif message_type == "interactive":
                # Handle interactive messages
                interactive = message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    button = interactive.get("button_reply", {})
                    # Create message data with button info as dict
                    message_data = {
                        "type": MessageType.INTERACTIVE.value,
                        "interactive_type": InteractiveType.BUTTON.value,
                        "button": {
                            "id": button.get("id"),
                            "title": button.get("title"),
                            "type": "reply"
                        }
                    }
                    message_data.update(base_data)

                    if logger.isEnabledFor(logging.DEBUG):
                        # Log serializable data
                        logger.debug(f"Extracted message data: {message_data}")
                        logger.debug(f"Channel type: {message_data['channel_type']}")
                        logger.debug(f"Mock testing: {message_data['mock_testing']}")

                    return message_data

            logger.debug(f"Skipping non-user message: {message.get('type')}")
            return {}

        except (IndexError, KeyError, ValueError) as e:
            # Get as much info as possible for error context
            value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
            messages = value.get("messages", [])
            message = messages[0] if messages else {}

            raise ComponentException(
                message=f"Invalid message payload format: {str(e)}",
                component="whatsapp_flow_processor",
                field="payload",
                value=str({
                    "error": str(e),
                    "payload": payload,
                    "value": value,
                    "message": message
                })
            )
