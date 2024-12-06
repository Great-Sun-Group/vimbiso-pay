#!/usr/bin/env python3
import argparse
import json
import requests
import sys
from datetime import datetime


def create_whatsapp_payload(
    phone_number,
    username,
    message_type,
    message_text,
    phone_number_id
):
    """Create a WhatsApp-style payload."""
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": phone_number_id,
                        "display_phone_number": "15550123456"
                    },
                    "contacts": [{
                        "wa_id": phone_number,
                        "profile": {
                            "name": username
                        }
                    }],
                    "messages": [{
                        "type": message_type,
                        "timestamp": int(datetime.now().timestamp()),
                        **get_message_content(message_type, message_text)
                    }]
                }
            }]
        }]
    }
    print("\nSending message:")
    print(f"From: {username} ({phone_number})")
    print(f"Message: {message_text}")
    print(f"Type: {message_type}")
    print(f"Phone Number ID: {phone_number_id}\n")
    return payload


def get_message_content(message_type, message_text):
    """Get the appropriate message content based on type."""
    if message_type == "text":
        return {"text": {"body": message_text}}
    elif message_type == "button":
        return {"button": {"payload": message_text}}
    elif message_type == "interactive":
        return {
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": message_text}
            }
        }
    else:
        print(f"Unsupported message type: {message_type}")
        sys.exit(1)


def send_message(args):
    """Send a message to the mock WhatsApp server."""
    payload = create_whatsapp_payload(
        args.phone,
        args.username,
        args.type,
        args.message,
        args.phone_number_id
    )

    url = f"http://localhost:{args.port}/webhook"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        print("Server Response:")
        print(json.dumps(response.json(), indent=2))

    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response text: {e.response.text}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Mock WhatsApp CLI Client")
    parser.add_argument(
        "--phone",
        default="1234567890",
        help="Phone number (default: 1234567890)"
    )
    parser.add_argument(
        "--username",
        default="CLI User",
        help="Username (default: CLI User)"
    )
    parser.add_argument(
        "--type",
        choices=["text", "button", "interactive"],
        default="text",
        help="Message type (default: text)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Server port (default: 8001)"
    )
    parser.add_argument(
        "--phone_number_id",
        default="123456789",
        help="WhatsApp Phone Number ID (default: 123456789)"
    )
    parser.add_argument(
        "message",
        help="Message to send"
    )

    args = parser.parse_args()
    send_message(args)


if __name__ == "__main__":
    main()
