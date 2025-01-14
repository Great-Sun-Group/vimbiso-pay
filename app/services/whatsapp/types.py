"""WhatsApp message types"""
import logging
from typing import Any, Dict, Optional

from core.messaging.exceptions import MessageValidationError
from core.messaging.types import Message as CoreMessage
from core.state.interface import StateManagerInterface

logger = logging.getLogger(__name__)


class WhatsAppMessage(Dict[str, Any]):
    """WhatsApp message format"""

    # WhatsApp API requires these exact string values
    WHATSAPP_BASE = {
        "messaging_product": "whatsapp",  # API string
        "recipient_type": "individual"
    }

    # WhatsApp Cloud API limits
    LIMITS = {
        "text_body": 4096,      # Maximum text message length
        "header": 60,           # Maximum header text length
        "footer": 60,           # Maximum footer text length
        "button_text": 20,      # Maximum button text length
        "list_title": 24,       # Maximum list item title length
        "list_description": 72,  # Maximum list item description length
        "buttons_count": 3,     # Maximum number of buttons
        "sections_count": 10,   # Maximum number of sections
        "rows_per_section": 10  # Maximum rows per section
    }

    @classmethod
    def validate_interactive(cls, interactive: Dict[str, Any]) -> None:
        """Validate interactive message structure and limits"""
        if not interactive.get("type"):
            raise MessageValidationError(
                message="Interactive message type is required",
                service="whatsapp",
                action="validate_interactive",
                validation_details={"error": "missing_type"}
            )

        # Validate body text
        body = interactive.get("body", {}).get("text", "")
        if len(body) > cls.LIMITS["text_body"]:
            raise MessageValidationError(
                message=f"Body text exceeds {cls.LIMITS['text_body']} characters",
                service="whatsapp",
                action="validate_interactive",
                validation_details={
                    "error": "text_too_long",
                    "field": "body",
                    "length": len(body),
                    "max_length": cls.LIMITS["text_body"]
                }
            )

        # Validate header if present
        if "header" in interactive:
            header_text = interactive["header"].get("text", "")
            if len(header_text) > cls.LIMITS["header"]:
                raise MessageValidationError(
                    message=f"Header text exceeds {cls.LIMITS['header']} characters",
                    service="whatsapp",
                    action="validate_interactive",
                    validation_details={
                        "error": "text_too_long",
                        "field": "header",
                        "length": len(header_text),
                        "max_length": cls.LIMITS["header"]
                    }
                )

        # Validate footer if present
        if "footer" in interactive:
            footer_text = interactive["footer"].get("text", "")
            if len(footer_text) > cls.LIMITS["footer"]:
                raise MessageValidationError(
                    message=f"Footer text exceeds {cls.LIMITS['footer']} characters",
                    service="whatsapp",
                    action="validate_interactive",
                    validation_details={
                        "error": "text_too_long",
                        "field": "footer",
                        "length": len(footer_text),
                        "max_length": cls.LIMITS["footer"]
                    }
                )

        # Validate action based on type
        action = interactive.get("action", {})
        if interactive["type"] == "button":
            buttons = action.get("buttons", [])
            if len(buttons) > cls.LIMITS["buttons_count"]:
                raise MessageValidationError(
                    message=f"Too many buttons (max {cls.LIMITS['buttons_count']})",
                    service="whatsapp",
                    action="validate_interactive",
                    validation_details={
                        "error": "too_many_buttons",
                        "count": len(buttons),
                        "max_count": cls.LIMITS["buttons_count"]
                    }
                )
            for button in buttons:
                if len(button["reply"]["title"]) > cls.LIMITS["button_text"]:
                    raise MessageValidationError(
                        message=f"Button text exceeds {cls.LIMITS['button_text']} characters",
                        service="whatsapp",
                        action="validate_interactive",
                        validation_details={
                            "error": "text_too_long",
                            "field": "button_text",
                            "text": button["reply"]["title"],
                            "length": len(button["reply"]["title"]),
                            "max_length": cls.LIMITS["button_text"]
                        }
                    )

        elif interactive["type"] == "list":
            # Validate button text for list
            button_text = action.get("button", "")
            if len(button_text) > cls.LIMITS["button_text"]:
                raise MessageValidationError(
                    message=f"List button text exceeds {cls.LIMITS['button_text']} characters",
                    service="whatsapp",
                    action="validate_interactive",
                    validation_details={
                        "error": "text_too_long",
                        "field": "button_text",
                        "text": button_text,
                        "length": len(button_text),
                        "max_length": cls.LIMITS["button_text"]
                    }
                )

            # Validate sections
            sections = action.get("sections", [])
            if len(sections) > cls.LIMITS["sections_count"]:
                raise MessageValidationError(
                    message=f"Too many sections (max {cls.LIMITS['sections_count']})",
                    service="whatsapp",
                    action="validate_interactive",
                    validation_details={
                        "error": "too_many_sections",
                        "count": len(sections),
                        "max_count": cls.LIMITS["sections_count"]
                    }
                )

            for section in sections:
                rows = section.get("rows", [])
                if len(rows) > cls.LIMITS["rows_per_section"]:
                    raise MessageValidationError(
                        message=f"Too many rows in section (max {cls.LIMITS['rows_per_section']})",
                        service="whatsapp",
                        action="validate_interactive",
                        validation_details={
                            "error": "too_many_rows",
                            "section": section.get("title", "Untitled Section"),
                            "count": len(rows),
                            "max_count": cls.LIMITS["rows_per_section"]
                        }
                    )

                for row in rows:
                    if len(row["title"]) > cls.LIMITS["list_title"]:
                        raise MessageValidationError(
                            message=f"List item title exceeds {cls.LIMITS['list_title']} characters",
                            service="whatsapp",
                            action="validate_interactive",
                            validation_details={
                                "error": "text_too_long",
                                "field": "list_title",
                                "text": row["title"],
                                "length": len(row["title"]),
                                "max_length": cls.LIMITS["list_title"]
                            }
                        )

                    if "description" in row and len(row["description"]) > cls.LIMITS["list_description"]:
                        raise MessageValidationError(
                            message=f"List item description exceeds {cls.LIMITS['list_description']} characters",
                            service="whatsapp",
                            action="validate_interactive",
                            validation_details={
                                "error": "text_too_long",
                                "field": "list_description",
                                "text": row["description"],
                                "length": len(row["description"]),
                                "max_length": cls.LIMITS["list_description"]
                            }
                        )

    @classmethod
    def create_message(
        cls,
        to: str,
        message_type: str = "text",
        **content: Any
    ) -> Dict[str, Any]:
        """Create a standardized WhatsApp message"""
        if not to:
            raise MessageValidationError(
                message="Recipient (to) is required",
                service="whatsapp",
                action="create_message",
                validation_details={
                    "error": "missing_recipient",
                    "message_type": message_type
                }
            )

        message = {
            **cls.WHATSAPP_BASE,
            "to": to,
            "type": message_type
        }

        if message_type == "text":
            text = content.get("text")
            if text is None:
                raise MessageValidationError(
                    message="Text content is required",
                    service="whatsapp",
                    action="create_message",
                    validation_details={
                        "error": "missing_text",
                        "message_type": message_type
                    }
                )
            if len(str(text)) > cls.LIMITS["text_body"]:
                raise MessageValidationError(
                    message=f"Text exceeds {cls.LIMITS['text_body']} characters",
                    service="whatsapp",
                    action="create_message",
                    validation_details={
                        "error": "text_too_long",
                        "length": len(str(text)),
                        "max_length": cls.LIMITS["text_body"]
                    }
                )
            message["text"] = {"body": str(text)}

        elif message_type == "interactive":
            interactive = content.get("interactive", {})
            cls.validate_interactive(interactive)
            message["interactive"] = interactive

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
    def from_core_message(cls, message: CoreMessage, state_manager: Optional[StateManagerInterface] = None) -> Dict[str, Any]:
        """Convert core Message to WhatsApp format

        Args:
            message: Core message to convert
            state_manager: Optional state manager for stateful operation

        Returns:
            Dict[str, Any]: WhatsApp formatted message
        """
        try:
            if not message or not message.content:
                raise MessageValidationError(
                    message="Message or content is missing",
                    service="whatsapp",
                    action="from_core_message",
                    validation_details={
                        "error": "missing_content",
                        "message": str(message)
                    }
                )

            # Get recipient info from message or state
            if message.recipient:
                channel_type = message.recipient.type
                channel_id = message.recipient.identifier
            elif state_manager:
                channel_type = state_manager.get_channel_type()
                channel_id = state_manager.get_channel_id()
            else:
                raise MessageValidationError(
                    message="No recipient found in message or state",
                    service="whatsapp",
                    action="from_core_message",
                    validation_details={
                        "error": "missing_recipient"
                    }
                )

            # Validate channel type
            if channel_type != "whatsapp":
                raise MessageValidationError(
                    message="Invalid channel type for WhatsApp message",
                    service="whatsapp",
                    action="from_core_message",
                    validation_details={
                        "error": "invalid_channel",
                        "expected": "whatsapp",
                        "received": channel_type
                    }
                )

            content = message.content
            content_type = content.type.value

            if content_type == "text":
                if not content.body:
                    raise MessageValidationError(
                        message="Text content body is required",
                        service="whatsapp",
                        action="from_core_message",
                        validation_details={
                            "error": "missing_text",
                            "content_type": content_type
                        }
                    )
                return cls.create_message(
                    to=channel_id,
                    message_type="text",
                    text=content.body
                )

            elif content_type == "interactive":
                # Handle both dict and object content
                if hasattr(content, 'to_dict'):
                    interactive_content = content.to_dict()["interactive"]
                else:
                    interactive_content = content.get("interactive", {})
                return cls.create_message(
                    to=channel_id,
                    message_type="interactive",
                    interactive=interactive_content
                )

            elif content_type == "template":
                return cls.create_message(
                    to=channel_id,
                    message_type="template",
                    template=content.to_dict()["template"]
                )

            elif content_type in ["image", "document", "audio", "video"]:
                return cls.create_message(
                    to=channel_id,
                    message_type=content_type,
                    url=content.url,
                    caption=getattr(content, "caption", None),
                    filename=getattr(content, "filename", None)
                )

            elif content_type == "location":
                return cls.create_message(
                    to=channel_id,
                    message_type="location",
                    latitude=content.latitude,
                    longitude=content.longitude,
                    name=getattr(content, "name", None),
                    address=getattr(content, "address", None)
                )

            else:
                raise MessageValidationError(
                    message=f"Unsupported message type: {content_type}",
                    service="whatsapp",
                    action="from_core_message",
                    validation_details={
                        "error": "unsupported_type",
                        "content_type": content_type,
                        "supported_types": ["text", "interactive", "template", "image", "document", "audio", "video", "location"]
                    }
                )

        except Exception as e:
            logger.error(f"Message conversion error: {str(e)}")
            # Get channel ID from message recipient or state
            channel_id = "unknown"
            try:
                if message and message.recipient:
                    channel_id = message.recipient.identifier
                elif state_manager:
                    channel_id = state_manager.get_state_value("channel", {}).get("identifier", "unknown")
            except Exception:
                pass  # Keep default "unknown" if both lookups fail

            return cls.create_text(
                channel_id,
                f"Error converting message: {str(e)}"
            )
