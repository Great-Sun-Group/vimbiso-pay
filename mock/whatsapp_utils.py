"""WhatsApp message formatting utilities."""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)


def create_message_template(
    phone_number: str,
    template_type: str,
    content: Dict[str, Any],
    header_text: str = None,
    footer_text: str = None
) -> Dict[str, Any]:
    """Create a WhatsApp message template strictly following WhatsApp Cloud API format."""
    template = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": template_type,
            "body": {"text": content.get("body_text", "")}
        }
    }

    # Add header if provided
    if header_text:
        template["interactive"]["header"] = {
            "type": "text",
            "text": header_text
        }

    # Add footer if provided
    if footer_text:
        template["interactive"]["footer"] = {
            "text": footer_text
        }

    # Add action based on type
    if template_type == "list":
        # Validate sections format
        sections = content.get("sections", [])
        if not isinstance(sections, list):
            raise ValueError("Sections must be a list")

        for section in sections:
            if "rows" not in section or not isinstance(section["rows"], list):
                raise ValueError("Each section must have a rows list")
            for row in section["rows"]:
                if "id" not in row or "title" not in row:
                    raise ValueError("Each row must have id and title")
                if len(row["title"]) > 24:
                    raise ValueError("Row title must not exceed 24 characters")

        template["interactive"]["action"] = {
            "button": content.get("button_text", "Select")[:20],  # Max 20 chars
            "sections": sections
        }

    elif template_type == "button":
        # Validate buttons format
        buttons = content.get("buttons", [])
        if not isinstance(buttons, list):
            raise ValueError("Buttons must be a list")
        if len(buttons) > 3:
            raise ValueError("Maximum 3 buttons allowed")

        formatted_buttons = []
        for button in buttons:
            if "id" not in button or "title" not in button:
                raise ValueError("Each button must have id and title")
            if len(button["title"]) > 20:
                raise ValueError("Button title must not exceed 20 characters")
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": button["id"],
                    "title": button["title"]
                }
            })

        template["interactive"]["action"] = {
            "buttons": formatted_buttons
        }

    return template


def create_whatsapp_payload(
    phone_number: str,
    message_type: str,
    message_text: Union[str, Dict],
    phone_number_id: str = "123456789"
) -> Dict[str, Any]:
    """Create a WhatsApp webhook payload following Cloud API format."""
    timestamp = str(int(datetime.now().timestamp()))
    message_id = f"wamid.{''.join(['0123456789ABCDEF'[int(timestamp) % 16] for _ in range(32)])}"

    # Get base message content
    message_content = _get_message_content(message_type, message_text)

    # Create the message object that matches WhatsApp webhook format
    message = {
        "from": phone_number,
        "id": message_id,
        "timestamp": timestamp,
        **message_content
    }

    # Wrap in webhook format
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": phone_number,
                        "phone_number_id": phone_number_id,
                        "timestamp": timestamp
                    },
                    "contacts": [{
                        "profile": {"name": "Test User"},
                        "wa_id": phone_number
                    }],
                    "messages": [message]
                },
                "field": "messages"
            }]
        }]
    }


def _get_message_content(message_type: str, message_text: Union[str, Dict]) -> Dict[str, Any]:
    """Get message content based on type following WhatsApp Cloud API format."""
    if message_type == "text":
        return {
            "type": "text",
            "text": {
                "body": message_text[:4096],  # WhatsApp's text limit
                "preview_url": False
            }
        }

    if message_type == "interactive":
        # Handle menu selection
        if isinstance(message_text, str) and message_text.startswith("handle_action_"):
            return {
                "type": "interactive",
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {
                        "id": message_text[:256],  # WhatsApp's ID limit
                        "title": message_text[:20]  # WhatsApp's title limit
                    }
                }
            }

        # Handle button/list replies
        if isinstance(message_text, str) and ":" in message_text:
            reply_type, reply_id = message_text.split(":", 1)
            if reply_type in ["button", "list"]:
                return {
                    "type": "interactive",
                    "interactive": {
                        "type": f"{reply_type}_reply",
                        f"{reply_type}_reply": {
                            "id": reply_id[:256],  # WhatsApp's ID limit
                            "title": reply_id[:20]  # WhatsApp's title limit
                        }
                    }
                }

        # Default to text message
        return {
            "type": "text",
            "text": {
                "body": str(message_text)[:4096],  # WhatsApp's text limit
                "preview_url": False
            }
        }

    raise ValueError(f"Unsupported message type: {message_type}")


def extract_message_text(message: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    """Extract message text from WhatsApp message following Cloud API format."""
    message_type = message.get("type", "")

    if message_type == "text":
        return message.get("text", {}).get("body", "")

    if message_type == "interactive":
        interactive = message.get("interactive", {})
        interactive_type = interactive.get("type", "")

        # Handle button/list replies
        if interactive_type == "button_reply":
            reply = interactive.get("button_reply", {})
            return reply.get("id", "")
        elif interactive_type == "list_reply":
            reply = interactive.get("list_reply", {})
            return reply.get("id", "")

        return "Unknown interactive type"

    return "Unsupported message type"


def format_json_response(response_text: str) -> Dict[str, Any]:
    """Format JSON response text."""
    try:
        # Parse response text
        data = json.loads(response_text)

        # Log the parsed data
        logger.debug(f"Parsed response data: {json.dumps(data, indent=2)}")

        # Extract response content
        if isinstance(data, dict):
            # If response is nested under 'response' key
            if 'response' in data:
                return data['response']
            return data

        return {"text": {"body": str(data)}}

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response: {e}")
        return {"text": {"body": response_text}}


def format_mock_response() -> Dict[str, Any]:
    """Format mock response following WhatsApp Cloud API format."""
    return {
        "messaging_product": "whatsapp",
        "contacts": [
            {
                "input": "263778177125",
                "wa_id": "263778177125"
            }
        ],
        "messages": [
            {
                "id": f"wamid.{''.join(['0123456789ABCDEF'[int(datetime.now().timestamp()) % 16] for _ in range(32)])}"
            }
        ]
    }
