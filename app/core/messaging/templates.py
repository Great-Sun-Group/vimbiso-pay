"""Message templates for progressive WhatsApp interactions"""
from typing import Any, Dict, List

from .types import (
    Message,
    MessageRecipient,
    TextContent,
    InteractiveContent,
    InteractiveType,
    Button
)


class ProgressiveInput:
    """Templates for progressive text input"""

    @staticmethod
    def create_prompt(text: str, examples: List[str], recipient: str) -> Message:
        """Create initial prompt with examples"""
        example_text = "\n".join([f"• {example}" for example in examples])
        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=TextContent(
                body=f"{text}\n\nExamples:\n{example_text}"
            )
        )

    @staticmethod
    def create_validation_error(error: str, recipient: str) -> Message:
        """Create validation error message"""
        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=TextContent(
                body=f"❌ {error}\n\nPlease try again."
            )
        )

    @staticmethod
    def create_confirmation(value: Any, recipient: str) -> Message:
        """Create value confirmation message with buttons"""
        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=f"Confirm value: {value}",
                buttons=[
                    Button(id="confirm", title="Confirm"),
                    Button(id="retry", title="Try Again")
                ]
            )
        )


class ListSelection:
    """Templates for list selection"""

    @staticmethod
    def create_list(params: Dict[str, Any], recipient: str) -> Message:
        """Create list selection message"""
        sections = []
        for section in params.get("sections", []):
            section_items = []
            for item in section.get("rows", []):
                list_item = {
                    "id": item["id"],
                    "title": item["title"]
                }
                if "description" in item:
                    list_item["description"] = item["description"]
                section_items.append(list_item)

            sections.append({
                "title": section["title"],
                "rows": section_items
            })

        # Create interactive content with proper button text
        content = InteractiveContent(
            interactive_type=InteractiveType.LIST,
            body=params.get("text", "Select an option:"),
            action_items=sections
        )
        # Set the button text from params or use default
        if "button" in params:
            content.action_items = {
                "button": params["button"],
                "sections": sections
            }
        else:
            content.action_items = {
                "button": "Select",
                "sections": sections
            }

        return Message(
            recipient=MessageRecipient(phone_number=recipient),
            content=content
        )


class ButtonSelection:
    """Templates for button selection"""

    @staticmethod
    def create_buttons(params: Dict[str, Any], recipient: str) -> Message:
        """Create button selection message following WhatsApp Cloud API format"""
        # Ensure we don't exceed WhatsApp's 3 button limit
        buttons = [
            Button(id=button["id"], title=button["title"])
            for button in params["buttons"][:3]  # WhatsApp limits to 3 buttons
        ]

        # Create message following WhatsApp Cloud API format
        message = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": params["text"]
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": button.id,
                                "title": button.title
                            }
                        }
                        for button in buttons
                    ]
                }
            }
        }

        # Add header if provided
        if "header" in params:
            message["interactive"]["header"] = {
                "type": "text",
                "text": params["header"]
            }

        # Add footer if provided
        if "footer" in params:
            message["interactive"]["footer"] = {
                "text": params["footer"]
            }

        return message
