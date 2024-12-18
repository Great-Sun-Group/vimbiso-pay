"""WhatsApp service types and interfaces"""
import json
import logging
from typing import Any, Dict, Union, Optional

from core.messaging.types import Message as CoreMessage

logger = logging.getLogger(__name__)


class WhatsAppMessage(Dict[str, Any]):
    """Type for WhatsApp messages"""

    WHATSAPP_BASE = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual"
    }

    @classmethod
    def create_message(
        cls,
        to: str,
        message_type: str = "text",
        **content: Any
    ) -> Dict[str, Any]:
        """Create a standardized WhatsApp message"""
        message = {
            **cls.WHATSAPP_BASE,
            "to": to,
            "type": message_type
        }

        if message_type == "text":
            message["text"] = {"body": str(content.get("text", ""))}
        elif message_type == "interactive":
            message["interactive"] = content.get("interactive", {})
        else:
            message[message_type] = content.get(message_type, {})

        return message

    @classmethod
    def create_text(cls, to: str, text: str) -> Dict[str, Any]:
        """Create a text message"""
        return cls.create_message(to, "text", text=text)

    @classmethod
    def create_button(
        cls,
        to: str,
        text: str,
        buttons: list,
        header: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a button message"""
        interactive = {
            "type": "button",
            "body": {"text": text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn.get("id", f"btn_{i}"),
                            "title": btn.get("title", "")[:20]  # WhatsApp limit
                        }
                    }
                    for i, btn in enumerate(buttons)
                ]
            }
        }
        if header:
            interactive["header"] = header

        return cls.create_message(to, "interactive", interactive=interactive)

    @classmethod
    def create_list(
        cls,
        to: str,
        text: str,
        button: str,
        sections: list,
        header: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a list message"""
        interactive = {
            "type": "list",
            "body": {"text": text},
            "action": {
                "button": button[:20],  # WhatsApp limit
                "sections": sections
            }
        }
        if header:
            interactive["header"] = header

        return cls.create_message(to, "interactive", interactive=interactive)

    @classmethod
    def from_core_message(cls, message: Union[CoreMessage, Dict[str, Any], 'WhatsAppMessage']) -> Dict[str, Any]:
        """Convert core message to WhatsApp format"""
        try:
            # Already in WhatsApp format
            if isinstance(message, dict) and "messaging_product" in message:
                return message

            # Dict but not in WhatsApp format
            if isinstance(message, dict):
                msg_type = message.get("type", "text")
                if msg_type == "text":
                    return cls.create_text(
                        message.get("to", ""),
                        str(message.get("body", message.get("text", {}).get("body", "")))
                    )
                return cls.create_message(
                    message.get("to", ""),
                    msg_type,
                    **{msg_type: message.get(msg_type, {})}
                )

            # Core message
            if isinstance(message, CoreMessage):
                content_type = message.content.type.value
                if content_type == "text":
                    return cls.create_text(
                        message.recipient.phone_number,
                        message.content.body
                    )
                return cls.create_message(
                    message.recipient.phone_number,
                    content_type,
                    **{content_type: message.content.to_dict()}
                )

            # WhatsAppMessage instance
            if isinstance(message, WhatsAppMessage):
                return dict(message)

            raise TypeError(f"Cannot convert {type(message)} to WhatsApp format")

        except Exception as e:
            logger.error(f"Message conversion error: {str(e)}")
            return cls.create_text("", f"Error converting message: {str(e)}")


class BotServiceInterface:
    """Interface for bot services"""

    def __init__(self, payload: Dict[str, Any], user: Any) -> None:
        """Initialize bot service"""
        self.message = payload
        self.user = user
        self._parse_message(payload)

    def _parse_message(self, payload: Dict[str, Any]) -> None:
        """Parse WhatsApp message payload"""
        try:
            # Extract message data
            message_data = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )
            messages = message_data.get("messages", [{}])
            if not messages:
                raise ValueError("No messages found in payload")

            message = messages[0]
            self.message_type = message.get("type", "")

            # Extract message content
            if self.message_type == "text":
                self.body = message.get("text", {}).get("body", "")
            elif self.message_type == "button":
                self.body = message.get("button", {}).get("payload", "")
            elif self.message_type == "interactive":
                self._parse_interactive(message.get("interactive", {}))
            else:
                logger.warning(f"Unsupported message type: {self.message_type}")
                self.body = ""

        except Exception as e:
            logger.error(f"Message parsing error: {str(e)}")
            self.message_type = "text"
            self.body = ""

    def _parse_interactive(self, interactive: Dict[str, Any]) -> None:
        """Parse interactive message content"""
        try:
            if "button_reply" in interactive:
                self.body = interactive["button_reply"].get("id", "")
            elif "list_reply" in interactive:
                self.body = interactive["list_reply"].get("id", "")
            elif "nfm_reply" in interactive:
                self.message_type = "nfm_reply"
                self.body = self._parse_form_data(interactive["nfm_reply"])
            else:
                self.body = ""
        except Exception as e:
            logger.error(f"Interactive parsing error: {str(e)}")
            self.body = ""

    def _parse_form_data(self, nfm_reply: Dict[str, Any]) -> Dict[str, Any]:
        """Parse form submission data"""
        form_data = {}
        try:
            # Parse submitted form data
            if "submitted_form_data" in nfm_reply:
                submitted_form = nfm_reply["submitted_form_data"]
                if "form_data" in submitted_form:
                    form_data_obj = submitted_form["form_data"]
                    if "response_fields" in form_data_obj:
                        for field in form_data_obj["response_fields"]:
                            if "field_id" in field and "value" in field:
                                form_data[field["field_id"]] = field["value"]
                    elif "response_payload" in form_data_obj:
                        payload = form_data_obj["response_payload"].get("response_json")
                        if payload:
                            form_data.update(json.loads(payload))

            # Parse direct response JSON
            elif "response_json" in nfm_reply:
                form_data.update(json.loads(nfm_reply["response_json"]))

        except Exception as e:
            logger.error(f"Form data parsing error: {str(e)}")

        return form_data

    def get_response_template(self, message_text: str) -> Dict[str, Any]:
        """Get WhatsApp message template"""
        # Check for button format
        if "\n\n[" in message_text and "]" in message_text:
            text, button = message_text.rsplit("\n\n", 1)
            button_id = button[1:button.index("]")].strip()
            button_label = button[button.index("]")+1:].strip()
            return WhatsAppMessage.create_button(
                self.user.mobile_number,
                text,
                [{"id": button_id, "title": button_label}]
            )

        # Default text message
        return WhatsAppMessage.create_text(self.user.mobile_number, message_text)

    def handle(self) -> Dict[str, Any]:
        """Process message and generate response"""
        raise NotImplementedError
