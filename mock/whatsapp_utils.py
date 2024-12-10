"""Shared utilities for WhatsApp mock implementations"""
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
    """Create a WhatsApp message template.

    Args:
        phone_number: Recipient's phone number
        template_type: Type of template (list, button)
        content: Template content (body_text, buttons/sections)
        header_text: Optional header text
        footer_text: Optional footer text
    """
    template = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": template_type,
            "body": {"text": content.get("body_text", "")},
            "action": {}
        }
    }

    if template_type == "list":
        template["interactive"]["action"].update({
            "button": content["button_text"],
            "sections": content["sections"]
        })
    elif template_type == "button":
        template["interactive"]["action"].update({
            "buttons": [
                {"type": "reply", "reply": button}
                for button in content["buttons"]
            ]
        })

    if header_text:
        template["interactive"]["header"] = {"type": "text", "text": header_text}
    if footer_text:
        template["interactive"]["footer"] = {"text": footer_text}

    return template


def create_whatsapp_payload(
    phone_number: str,
    message_type: str,
    message_text: Union[str, Dict],
    phone_number_id: str = "123456789"
) -> Dict[str, Any]:
    """Create a WhatsApp webhook payload."""
    timestamp = str(int(datetime.now().timestamp()))
    message_id = f"wamid.{''.join(['0123456789ABCDEF'[int(timestamp) % 16] for _ in range(32)])}"

    message_content = _get_message_content(message_type, message_text)

    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15550123456",
                        "phone_number_id": phone_number_id,
                        "timestamp": timestamp
                    },
                    "contacts": [{
                        "profile": {"name": ""},
                        "wa_id": phone_number,
                        "input": phone_number
                    }],
                    "messages": [{
                        "from": phone_number,
                        "id": message_id,
                        "timestamp": timestamp,
                        "type": message_type,
                        "context": {
                            "from": phone_number,
                            "id": message_id,
                            "forwarded": False,
                            "frequently_forwarded": False
                        },
                        **message_content
                    }]
                },
                "field": "messages"
            }]
        }]
    }


def _get_message_content(message_type: str, message_text: Union[str, Dict]) -> Dict[str, Any]:
    """Get message content based on type."""
    if message_type == "text":
        return {"text": {"body": message_text, "preview_url": False}}

    if message_type == "interactive":
        # Handle menu selection (e.g., "handle_action_offer_credex")
        if isinstance(message_text, str) and message_text.startswith("handle_action_"):
            return {
                "interactive": {
                    "type": "button_reply",
                    "button_reply": {
                        "id": message_text,
                        "title": message_text
                    }
                }
            }

        # Handle form data
        if isinstance(message_text, dict):
            return {
                "interactive": {
                    "type": "nfm_reply",
                    "nfm_reply": _create_form_reply(message_text)
                }
            }

        # Handle button/list replies with explicit type
        if isinstance(message_text, str) and ":" in message_text:
            reply_type, reply_id = message_text.split(":", 1)
            if reply_type in ["button", "list"]:
                return {
                    "interactive": {
                        "type": f"{reply_type}_reply",
                        f"{reply_type}_reply": {
                            "id": reply_id,
                            "title": reply_id
                        }
                    }
                }

        # Default to text message
        return {"text": {"body": str(message_text), "preview_url": False}}

    raise ValueError(f"Unsupported message type: {message_type}")


def _create_form_reply(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create form reply structure."""
    timestamp = str(int(datetime.now().timestamp()))
    return {
        "submitted_form_data": {
            "response_at": timestamp,
            "form_data": {
                "version": "1",
                "screen": "MAIN",
                "response_payload": {
                    "response_json": json.dumps(form_data),
                    "version": "1"
                },
                "response_fields": [
                    {
                        "field_id": field_id,
                        "value": value,
                        "type": "text",
                        "screen": "MAIN",
                        "version": "1",
                        "selected": True
                    } for field_id, value in form_data.items()
                ]
            }
        }
    }


def extract_message_text(message: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    """Extract message text from WhatsApp message."""
    message_type = message.get("type", "")

    if message_type == "text":
        return message.get("text", {}).get("body", "")

    if message_type == "interactive":
        interactive = message.get("interactive", {})
        interactive_type = interactive.get("type", "")

        # Handle button/list replies
        if interactive_type == "button_reply":
            return interactive["button_reply"].get("id", "")
        elif interactive_type == "list_reply":
            return interactive["list_reply"].get("id", "")

        # Handle form replies
        elif interactive_type == "nfm_reply":
            nfm_reply = interactive.get("nfm_reply", {})
            submitted_data = nfm_reply.get("submitted_form_data", {})
            form_data = submitted_data.get("form_data", {})

            # Try to get response from response_payload first
            if "response_payload" in form_data:
                try:
                    return json.loads(form_data["response_payload"]["response_json"])
                except (json.JSONDecodeError, KeyError):
                    pass

            # Fallback to response_fields
            response_fields = form_data.get("response_fields", [])
            return {
                field["field_id"]: field["value"]
                for field in response_fields
                if "field_id" in field and "value" in field
            }

        return "Unknown interactive type"

    return "Unsupported message type"


def format_json_response(response_text: str) -> Dict[str, Any]:
    """Format JSON response."""
    try:
        data = json.loads(response_text)
        return data.get("response", data) if isinstance(data, dict) else data
    except json.JSONDecodeError:
        return {
            "type": "text",
            "text": {
                "body": response_text,
                "preview_url": False
            }
        }
