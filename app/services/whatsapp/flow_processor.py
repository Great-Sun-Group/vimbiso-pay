"""WhatsApp-specific flow processor implementation"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.flow.processor import FlowProcessor

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
            if message.get("type") == "text" and "from" in message:
                return message

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
