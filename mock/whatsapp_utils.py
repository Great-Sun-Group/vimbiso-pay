"""Shared utilities for WhatsApp mock implementations"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List


# Set up logging
logger = logging.getLogger(__name__)


def create_menu_template(
    phone_number: str,
    body_text: str,
    button_text: str,
    sections: List[Dict[str, Any]],
    header_text: str = None,
    footer_text: str = None
) -> Dict[str, Any]:
    """Create a WhatsApp menu template message.

    Args:
        phone_number: Recipient's phone number
        body_text: Main message text
        button_text: Text for the menu button
        sections: List of menu sections with options
        header_text: Optional header text
        footer_text: Optional footer text

    Returns:
        Dict[str, Any]: WhatsApp menu message format
    """
    menu = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
    }

    if header_text:
        menu["interactive"]["header"] = {
            "type": "text",
            "text": header_text
        }

    if footer_text:
        menu["interactive"]["footer"] = {
            "text": footer_text
        }

    return menu


def create_button_template(
    phone_number: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: str = None,
    footer_text: str = None
) -> Dict[str, Any]:
    """Create a WhatsApp button template message.

    Args:
        phone_number: Recipient's phone number
        body_text: Main message text
        buttons: List of button objects with id and title
        header_text: Optional header text
        footer_text: Optional footer text

    Returns:
        Dict[str, Any]: WhatsApp button message format
    """
    button_msg = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": button
                    } for button in buttons
                ]
            }
        }
    }

    if header_text:
        button_msg["interactive"]["header"] = {
            "type": "text",
            "text": header_text
        }

    if footer_text:
        button_msg["interactive"]["footer"] = {
            "text": footer_text
        }

    return button_msg


def create_whatsapp_payload(phone_number, message_type, message_text, phone_number_id="123456789"):
    """Create a WhatsApp-style payload.

    Args:
        phone_number: The user's phone number
        message_type: Type of message (text, button, interactive)
        message_text: The message content
        phone_number_id: WhatsApp phone number ID

    Returns:
        dict: WhatsApp message payload
    """
    timestamp = int(datetime.now().timestamp())
    # WhatsApp message IDs are 32-char hex strings
    message_id = f"wamid.{''.join(['0123456789ABCDEF'[timestamp % 16] for _ in range(32)])}"

    # Create payload matching real WhatsApp webhook format
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550123456",
                                "phone_number_id": phone_number_id,
                                "timestamp": str(timestamp)  # WhatsApp uses string timestamps
                            },
                            "statuses": [],  # Required by WhatsApp
                            "contacts": [
                                {
                                    "profile": {
                                        "name": ""  # WhatsApp may include additional profile fields
                                    },
                                    "wa_id": phone_number,
                                    "input": phone_number,  # Required by WhatsApp
                                }
                            ],
                            "messages": [
                                {
                                    "from": phone_number,
                                    "id": message_id,
                                    "timestamp": str(timestamp),
                                    "type": message_type,
                                    "context": {
                                        "from": phone_number,
                                        "id": message_id,
                                        "forwarded": False,  # Required by WhatsApp
                                        "frequently_forwarded": False  # Required by WhatsApp
                                    },
                                    **get_message_content(message_type, message_text)
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    # Log the payload for debugging
    logger.debug("\nCreated WhatsApp payload:")
    logger.debug(f"Phone: {phone_number}")
    logger.debug(f"Message: {message_text}")
    logger.debug(f"Type: {message_type}")
    logger.debug(f"Phone Number ID: {phone_number_id}\n")

    return payload


def get_message_content(message_type, message_text):
    """Get the appropriate message content based on type.

    Args:
        message_type: Type of message (text, button, interactive)
        message_text: The message content

    Returns:
        dict: Message content structure
    """
    if message_type == "text":
        return {
            "text": {
                "body": message_text,
                "preview_url": False  # Required by WhatsApp
            }
        }
    elif message_type == "button":
        return {
            "button": {
                "payload": message_text,
                "text": message_text  # Required by WhatsApp
            }
        }
    elif message_type == "interactive":
        # Handle different interactive message types
        if message_text.startswith("button:"):
            # Format: button:button_id
            button_id = message_text.split(":", 1)[1]
            return {
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {
                        "id": button_id,
                        "title": button_id,
                        "description": None,  # Optional in WhatsApp
                        "selected": True  # Required by WhatsApp for replies
                    }
                }
            }
        elif message_text.startswith("list:"):
            # Format: list:selection_id
            selection_id = message_text.split(":", 1)[1]
            return {
                "interactive": {
                    "type": "list_reply",
                    "list_reply": {
                        "id": selection_id,
                        "title": selection_id,
                        "description": None,  # Optional in WhatsApp
                        "selected": True  # Required by WhatsApp for replies
                    }
                }
            }
        elif message_text.startswith("form:"):
            # Format: form:field1=value1,field2=value2
            form_data = {}
            data_str = message_text.split(":", 1)[1]
            if data_str:
                for field in data_str.split(","):
                    if "=" in field:
                        key, value = field.split("=", 1)
                        form_data[key.strip()] = value.strip()

            # Match WhatsApp's exact NFM reply format
            return {
                "interactive": {
                    "type": "nfm_reply",
                    "nfm_reply": {
                        "submitted_form_data": {
                            "message_id": None,  # Optional in WhatsApp
                            "response_at": str(int(datetime.now().timestamp())),  # Required by WhatsApp
                            "form_data": {
                                "version": "1",  # Required by WhatsApp
                                "screen": "MAIN",  # Required by WhatsApp
                                "name": "credex_offer_form",  # Match form name from forms.py
                                "response_payload": {
                                    "response_json": json.dumps(form_data),
                                    "version": "1"  # Required by WhatsApp
                                },
                                "response_fields": [
                                    {
                                        "field_id": field_id,
                                        "value": value,
                                        "type": "text",  # Match field type from forms.py
                                        "screen": "MAIN",  # Required by WhatsApp
                                        "version": "1",  # Required by WhatsApp
                                        "selected": True  # Required by WhatsApp for form fields
                                    } for field_id, value in form_data.items()
                                ]
                            }
                        }
                    }
                }
            }
        else:
            # Default to button reply
            return {
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {
                        "id": message_text,
                        "title": message_text,
                        "description": None,  # Optional in WhatsApp
                        "selected": True  # Required by WhatsApp for replies
                    }
                }
            }
    else:
        raise ValueError(f"Unsupported message type: {message_type}")


def format_json_response(response_text):
    """Format JSON response.

    Args:
        response_text: JSON string to format

    Returns:
        dict: Parsed response object
    """
    try:
        # Parse the response text
        data = json.loads(response_text)

        # If it's a WhatsApp response wrapped in "response" key, return the inner response
        if isinstance(data, dict) and 'response' in data:
            return data['response']

        # Otherwise return the original data
        return data
    except json.JSONDecodeError:
        # Return error message as text response
        return {
            "type": "text",
            "text": {
                "body": response_text,
                "preview_url": False  # Required by WhatsApp
            }
        }


def extract_message_text(message):
    """Extract message text from a WhatsApp message based on its type.

    Args:
        message: WhatsApp message object

    Returns:
        str: Extracted message text
    """
    message_type = message.get("type", "")

    if message_type == "text":
        return message.get("text", {}).get("body", "")
    elif message_type == "button":
        return message.get("button", {}).get("payload", "")
    elif message_type == "interactive":
        interactive = message.get("interactive", {})
        if "button_reply" in interactive:
            return interactive["button_reply"].get("id", "")
        elif "list_reply" in interactive:
            return interactive["list_reply"].get("id", "")
        elif "nfm_reply" in interactive:
            # Extract form data from WhatsApp's NFM reply format
            submitted_form = interactive["nfm_reply"].get("submitted_form_data", {})
            form_data = submitted_form.get("form_data", {})

            # Get form name and version for validation
            form_name = form_data.get("name", "")
            version = form_data.get("version", "1")  # Used for version validation
            response_fields = form_data.get("response_fields", [])

            # Convert response fields to dictionary
            form_values = {}
            for field in response_fields:
                # Only process fields matching the form version
                if field.get("version") == version:
                    field_id = field.get("field_id")
                    value = field.get("value")
                    if field_id and value:
                        form_values[field_id] = value

            # For credex offer form, ensure required fields
            if form_name == "credex_offer_form":
                if "amount" not in form_values or "recipientAccountHandle" not in form_values:
                    logger.error("Missing required fields in credex offer form")
                    return {}

            return form_values
        else:
            return "Unknown interactive type"
    else:
        return "Unsupported message type"
