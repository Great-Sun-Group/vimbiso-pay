"""Shared utilities for WhatsApp mock implementations"""
import json
import logging
from datetime import datetime


# Set up logging
logger = logging.getLogger(__name__)


def create_whatsapp_payload(phone_number, username, message_type, message_text, phone_number_id="123456789"):
    """Create a WhatsApp-style payload.

    Args:
        phone_number: The user's phone number
        username: The user's display name
        message_type: Type of message (text, button, interactive)
        message_text: The message content
        phone_number_id: WhatsApp phone number ID

    Returns:
        dict: WhatsApp message payload
    """
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {
                                "phone_number_id": phone_number_id,
                                "display_phone_number": "15550123456",
                            },
                            "contacts": [
                                {"wa_id": phone_number, "profile": {"name": username}}
                            ],
                            "messages": [
                                {
                                    "type": message_type,
                                    "timestamp": int(datetime.now().timestamp()),
                                    **get_message_content(message_type, message_text),
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }

    # Log the payload for debugging
    logger.debug("\nCreated WhatsApp payload:")
    logger.debug(f"From: {username} ({phone_number})")
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
        return {"text": {"body": message_text}}
    elif message_type == "button":
        return {"button": {"payload": message_text}}
    elif message_type == "interactive":
        # Handle different interactive message types
        if message_text.startswith("button:"):
            # Format: button:button_id
            button_id = message_text.split(":", 1)[1]
            return {
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {"id": button_id}
                }
            }
        elif message_text.startswith("list:"):
            # Format: list:selection_id
            selection_id = message_text.split(":", 1)[1]
            return {
                "interactive": {
                    "type": "list_reply",
                    "list_reply": {"id": selection_id}
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

            return {
                "interactive": {
                    "type": "nfm_reply",
                    "nfm_reply": {
                        "response_json": json.dumps(form_data)
                    }
                }
            }
        else:
            # Default to button reply
            return {
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {"id": message_text}
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
            "text": {"body": response_text}
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
            return f"Form data: {interactive['nfm_reply'].get('response_json', '{}')}"
        else:
            return "Unknown interactive type"
    else:
        return "Unsupported message type"
