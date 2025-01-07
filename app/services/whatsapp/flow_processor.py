"""WhatsApp-specific flow processor implementation"""

from typing import Any, Dict

from core.messaging.flow_processor import FlowProcessor
from core.utils.exceptions import ComponentException


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
                value="None"
            )

        try:
            value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
            return value.get("messages", [{}])[0]
        except Exception:
            raise ComponentException(
                message="Invalid message payload format",
                component="whatsapp_flow_processor",
                field="payload",
                value=str(payload)
            )
