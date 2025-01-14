"""Message templates for progressive WhatsApp interactions"""
from typing import Any, Dict, List

from core.messaging.types import (
    Message,
    MessageRecipient,
    TextContent,
    InteractiveContent,
    InteractiveType,
    Button,
    Section
)


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


class ProgressiveInput:
    """Templates for progressive text input"""

    @staticmethod
    def create_prompt(text: str, examples: List[str], channel_identifier: str) -> Message:
        """Create initial prompt with examples"""
        example_text = "\n".join([f"• {example}" for example in examples])
        full_text = f"{text}\n\nExamples:\n{example_text}"

        # Ensure text doesn't exceed WhatsApp limit
        if len(full_text) > LIMITS["text_body"]:
            full_text = full_text[:LIMITS["text_body"]]

        return Message(
            recipient=MessageRecipient(
                type="whatsapp",
                identifier=channel_identifier
            ),
            content=TextContent(
                body=full_text
            )
        )

    @staticmethod
    def create_validation_error(error: str, channel_identifier: str) -> Message:
        """Create validation error message"""
        error_text = f"❌ {error}\n\nPlease try again."

        # Ensure error text doesn't exceed limit
        if len(error_text) > LIMITS["text_body"]:
            error_text = error_text[:LIMITS["text_body"]]

        return Message(
            recipient=MessageRecipient(
                type="whatsapp",
                identifier=channel_identifier
            ),
            content=TextContent(
                body=error_text
            )
        )

    @staticmethod
    def create_confirmation(value: Any, channel_identifier: str) -> Message:
        """Create value confirmation message with buttons"""
        body_text = f"Confirm value: {value}"

        # Ensure body text doesn't exceed limit
        if len(body_text) > LIMITS["text_body"]:
            body_text = body_text[:LIMITS["text_body"]]

        return Message(
            recipient=MessageRecipient(
                type="whatsapp",
                identifier=channel_identifier
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body=body_text,
                buttons=[
                    Button(id="confirm", title="✅ Confirm"),
                    Button(id="retry", title="🔄 Try Again")
                ]
            )
        )


class ListSelection:
    """Templates for list selection"""

    @staticmethod
    def create_list(params: Dict[str, Any], channel_identifier: str) -> Message:
        """Create list selection message"""
        # Validate and truncate body text
        body_text = params.get("text", "Select an option:")
        if len(body_text) > LIMITS["text_body"]:
            body_text = body_text[:LIMITS["text_body"]]

        # Validate button text
        button_text = params.get("button", "Select")
        if len(button_text) > LIMITS["button_text"]:
            button_text = button_text[:LIMITS["button_text"]]

        # Process sections with validation
        sections = []
        section_count = 0
        for section in params.get("sections", []):
            if section_count >= LIMITS["sections_count"]:
                break

            # Validate section title
            section_title = section.get("title", "")
            if len(section_title) > LIMITS["list_title"]:
                section_title = section_title[:LIMITS["list_title"]]

            # Process rows with validation
            section_items = []
            row_count = 0
            for item in section.get("rows", []):
                if row_count >= LIMITS["rows_per_section"]:
                    break

                # Validate title and description
                title = item.get("title", "")[:LIMITS["list_title"]]
                description = item.get("description", "")
                if description and len(description) > LIMITS["list_description"]:
                    description = description[:LIMITS["list_description"]]

                list_item = {
                    "id": item["id"],
                    "title": title
                }
                if description:
                    list_item["description"] = description

                section_items.append(list_item)
                row_count += 1

            sections.append(Section(
                title=section_title,
                rows=section_items
            ))
            section_count += 1

        # Create interactive content
        content = InteractiveContent(
            interactive_type=InteractiveType.LIST,
            body=body_text,
            sections=sections,
            button_text=button_text,
            header=params.get("header"),
            footer=params.get("footer")
        )

        # Validate header/footer if present
        if content.header and len(content.header) > LIMITS["header"]:
            content.header = content.header[:LIMITS["header"]]
        if content.footer and len(content.footer) > LIMITS["footer"]:
            content.footer = content.footer[:LIMITS["footer"]]

        return Message(
            recipient=MessageRecipient(
                type="whatsapp",
                identifier=channel_identifier
            ),
            content=content
        )


class ButtonSelection:
    """Templates for button selection"""

    @staticmethod
    def create_buttons(params: Dict[str, Any], channel_identifier: str) -> Message:
        """Create button selection message following WhatsApp Cloud API format"""
        # Validate and truncate body text
        body_text = params.get("text", "")
        if len(body_text) > LIMITS["text_body"]:
            body_text = body_text[:LIMITS["text_body"]]

        # Process buttons with validation
        buttons = []
        button_count = 0
        for button in params.get("buttons", []):
            if button_count >= LIMITS["buttons_count"]:
                break

            # Validate button title
            title = button.get("title", "")
            if len(title) > LIMITS["button_text"]:
                title = title[:LIMITS["button_text"]]

            buttons.append(Button(
                id=button["id"],
                title=title
            ))
            button_count += 1

        # Create interactive content
        content = InteractiveContent(
            interactive_type=InteractiveType.BUTTON,
            body=body_text,
            buttons=buttons,
            header=params.get("header"),
            footer=params.get("footer")
        )

        # Validate header/footer if present
        if content.header and len(content.header) > LIMITS["header"]:
            content.header = content.header[:LIMITS["header"]]
        if content.footer and len(content.footer) > LIMITS["footer"]:
            content.footer = content.footer[:LIMITS["footer"]]

        return Message(
            recipient=MessageRecipient(
                type="whatsapp",
                identifier=channel_identifier
            ),
            content=content
        )
