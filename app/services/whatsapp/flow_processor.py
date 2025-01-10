"""WhatsApp-specific flow processor implementation"""

from typing import Any, Dict

from core.flow.processor import FlowProcessor
from core.error.exceptions import ComponentException


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

            messages = value.get("messages", [])
            if not messages:
                raise ValueError("Missing messages array")

            message = messages[0]
            if not message:
                raise ValueError("Empty message object")

            return message

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
