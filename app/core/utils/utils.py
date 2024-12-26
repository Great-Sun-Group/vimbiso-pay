"""Utility functions and WhatsApp service implementation."""
import json
import logging
from datetime import datetime

import requests
from decouple import config


logger = logging.getLogger(__name__)


def format_synopsis(synopsis, style=None, max_line_length=35):
    formatted_synopsis = ""
    words = synopsis.split()
    line_length = 0

    for word in words:
        if line_length + len(word) + 1 > max_line_length:
            formatted_synopsis += "\n"
            line_length = 0
        if style:
            word = f"{style}{word}{style}"
        formatted_synopsis += word + " "
        line_length += len(word) + 1

    return formatted_synopsis.strip()


def wrap_text(
    message,
    channel_identifier,  # Channel identifier from state as SINGLE SOURCE OF TRUTH
    proceed_option=False,
    x_is_menu=False,
    navigate_is="Respond",
    extra_rows=[],
    use_buttons=False,
    yes_or_no=False,
    custom=dict,
    plain=False,
    include_menu=True,
):
    """Wrap text message with WhatsApp formatting

    Args:
        message: Text message to wrap
        channel_identifier: Channel identifier from state (e.g. WhatsApp number)
        proceed_option: Whether to include proceed option
        x_is_menu: Whether X button is menu
        navigate_is: Navigation button text
        extra_rows: Additional row options
        use_buttons: Whether to use button format
        yes_or_no: Whether to show yes/no buttons
        custom: Custom button configuration
        plain: Whether to use plain text format
        include_menu: Whether to include menu option

    Returns:
        Dict: Formatted WhatsApp message
    """
    logger.debug(f"Wrapping text message: {message}")
    if use_buttons:
        rows = [
            {"type": "reply", "reply": {"id": "N", "title": "❌ No"}},
            {"type": "reply", "reply": {"id": "Y", "title": "✅ Yes"}},
        ]
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_identifier,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {
                    "buttons": (
                        [
                            {
                                "type": "reply",
                                "reply": (
                                    custom
                                    if custom
                                    else {
                                        "id": "X",
                                        "title": (
                                            "🏡 Menu" if x_is_menu else "❌ Cancel"
                                        ),
                                    }
                                ),
                            }
                        ]
                        if not yes_or_no
                        else rows
                    )
                },
            },
        }

    if len(message) > 1024 or plain:
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_identifier,
            "type": "text",
            "text": {"body": message},
        }

    rows = extra_rows

    if proceed_option:
        rows.append({"id": "Y", "title": "✅ Continue"})

    if include_menu:
        rows.append({"id": "X", "title": "🏡 Menu"})

    row_data = []
    keystore = []
    for row in rows:
        if row.get("id") not in keystore:
            row_data.append(row)
            keystore.append(row.get("id"))

    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": channel_identifier,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": message},
            "action": {
                "button": f"🕹️ {navigate_is}",
                "sections": [{"title": "Control", "rows": row_data}],
            },
        },
    }


class CredexWhatsappService:
    def __init__(self, payload, phone_number_id=None):
        self.phone_number_id = phone_number_id or config("WHATSAPP_PHONE_NUMBER_ID")
        self.payload = payload
        # Update API version to v20.0
        self.api_url = config(
            "WHATSAPP_API_URL", default="https://graph.facebook.com/v20.0/"
        )
        logger.debug(f"Initialized WhatsApp service with phone_number_id: {self.phone_number_id}")

    def send_message(self):
        """Send message to WhatsApp Cloud API with detailed logging."""
        url = f"{self.api_url}{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {config('WHATSAPP_ACCESS_TOKEN')}",
            "Content-Type": "application/json",
        }

        # Log the exact request we're sending
        logger.info("WhatsApp request: %s", json.dumps({
            "url": url,
            "headers": {k: v for k, v in headers.items() if k != "Authorization"},
            "payload": self.payload
        }, indent=2))

        try:
            response = requests.post(url, json=self.payload, headers=headers)

            # Log the complete response
            logger.info("WhatsApp response: %s", json.dumps(response.json(), indent=2))

            if response.status_code != 200:
                logger.error("WhatsApp API Error [%d]: %s",
                             response.status_code, response.text)
            return response.json()

        except Exception as e:
            logger.error("Error sending WhatsApp message: %s", str(e))
            return {"error": str(e)}

    def notify(self):
        """Send notification message."""
        return self.send_message()


def convert_timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")


def format_denomination(amount, denomination):
    if denomination.upper() == "USD":
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {denomination}"


def validate_channel_identifier(identifier):
    """Validate channel identifier format

    Args:
        identifier: Channel identifier to validate

    Returns:
        bool: True if valid, False otherwise
    """
    # Basic validation for WhatsApp numbers
    # Can be extended for other channel types
    return (
        identifier.startswith("+")
        and len(identifier) >= 10
        and identifier[1:].isdigit()
    )


def mask_sensitive_info(text, mask_char="*"):
    # Example implementation, can be customized based on specific requirements
    words = text.split()
    masked_words = []
    for word in words:
        if len(word) > 4:
            masked_word = word[:2] + mask_char * (len(word) - 4) + word[-2:]
        else:
            masked_word = mask_char * len(word)
        masked_words.append(masked_word)
    return " ".join(masked_words)


def handle_api_error(response):
    if response.status_code >= 400:
        error_message = f"API Error: {response.status_code}"
        try:
            error_data = response.json()
            if "error" in error_data:
                error_message += f" - {error_data['error']}"
        except ValueError:
            error_message += f" - {response.text}"
        return error_message
    return None
