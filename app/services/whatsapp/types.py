"""WhatsApp message types"""
import logging
from typing import Any, Dict

from core.messaging.exceptions import MessageValidationError
from core.messaging.types import Message as CoreMessage

logger = logging.getLogger(__name__)


class WhatsAppMessage(Dict[str, Any]):
    """WhatsApp message format"""

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
        if not to:
            raise MessageValidationError("Recipient (to) is required")

        message = {
            **cls.WHATSAPP_BASE,
            "to": to,
            "type": message_type
        }

        if message_type == "text":
            message["text"] = {"body": str(content.get("text", ""))}
        elif message_type == "interactive":
            message["interactive"] = content.get("interactive", {})
        elif message_type == "template":
            message["template"] = content.get("template", {})
        elif message_type in ["image", "document", "audio", "video"]:
            message[message_type] = {
                "link": content.get("url", ""),
                **({"caption": content.get("caption")} if content.get("caption") else {}),
                **({"filename": content.get("filename")} if content.get("filename") else {})
            }
        elif message_type == "location":
            message["location"] = {
                "latitude": content.get("latitude", 0),
                "longitude": content.get("longitude", 0),
                **({"name": content.get("name")} if content.get("name") else {}),
                **({"address": content.get("address")} if content.get("address") else {})
            }
        else:
            message[message_type] = content.get(message_type, {})

        return message

    @classmethod
    def create_text(cls, to: str, text: str) -> Dict[str, Any]:
        """Create a text message"""
        return cls.create_message(to, "text", text=text)

    @classmethod
    def from_core_message(cls, message: CoreMessage) -> Dict[str, Any]:
        """Convert core Message to WhatsApp format"""
        try:
            content = message.content
            content_type = content.type.value

            if content_type == "text":
                return cls.create_message(
                    to=message.recipient.channel_value,
                    message_type="text",
                    text=content.body
                )
            elif content_type == "interactive":
                return cls.create_message(
                    to=message.recipient.channel_value,
                    message_type="interactive",
                    interactive=content.to_dict()["interactive"]
                )
            elif content_type == "template":
                return cls.create_message(
                    to=message.recipient.channel_value,
                    message_type="template",
                    template=content.to_dict()["template"]
                )
            elif content_type in ["image", "document", "audio", "video"]:
                return cls.create_message(
                    to=message.recipient.channel_value,
                    message_type=content_type,
                    url=content.url,
                    caption=getattr(content, "caption", None),
                    filename=getattr(content, "filename", None)
                )
            elif content_type == "location":
                return cls.create_message(
                    to=message.recipient.channel_value,
                    message_type="location",
                    latitude=content.latitude,
                    longitude=content.longitude,
                    name=getattr(content, "name", None),
                    address=getattr(content, "address", None)
                )
            else:
                raise MessageValidationError(f"Unsupported message type: {content_type}")

        except Exception as e:
            logger.error(f"Message conversion error: {str(e)}")
            return cls.create_text(
                message.recipient.channel_value,
                f"Error converting message: {str(e)}"
            )
