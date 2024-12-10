"""Message templates for progressive WhatsApp interactions"""
from typing import Any, Dict, List

from .types import Message as WhatsAppMessage


class ProgressiveInput:
    """Templates for progressive text input"""

    @staticmethod
    def create_prompt(text: str, examples: List[str]) -> WhatsAppMessage:
        """Create initial prompt with examples"""
        example_text = "\n".join([f"• {example}" for example in examples])
        return WhatsAppMessage(
            content={
                "type": "text",
                "text": {
                    "body": f"{text}\n\nExamples:\n{example_text}"
                }
            }
        )

    @staticmethod
    def create_validation_error(error: str) -> WhatsAppMessage:
        """Create validation error message"""
        return WhatsAppMessage(
            content={
                "type": "text",
                "text": {
                    "body": f"❌ {error}\n\nPlease try again."
                }
            }
        )

    @staticmethod
    def create_confirmation(value: Any) -> WhatsAppMessage:
        """Create value confirmation message with buttons"""
        return WhatsAppMessage(
            content={
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": f"Confirm value: {value}"
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "confirm",
                                    "title": "Confirm"
                                }
                            },
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "retry",
                                    "title": "Try Again"
                                }
                            }
                        ]
                    }
                }
            }
        )


class ListSelection:
    """Templates for list selection"""

    @staticmethod
    def create_list(params: Dict[str, Any]) -> WhatsAppMessage:
        """Create list selection message"""
        sections = []
        for section in params["sections"]:
            section_items = []
            for item in section["items"]:
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

        return WhatsAppMessage(
            content={
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": params["title"]
                    },
                    "action": {
                        "button": params.get("button", "Select"),
                        "sections": sections
                    }
                }
            }
        )


class ButtonSelection:
    """Templates for button selection"""

    @staticmethod
    def create_buttons(params: Dict[str, Any]) -> WhatsAppMessage:
        """Create button selection message"""
        buttons = []
        for button in params["buttons"]:
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": button["id"],
                    "title": button["title"]
                }
            })

        return WhatsAppMessage(
            content={
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": params["text"]
                    },
                    "action": {
                        "buttons": buttons[:3]  # WhatsApp limits to 3 buttons
                    }
                }
            }
        )
