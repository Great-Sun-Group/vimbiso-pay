#!/usr/bin/env python3
import argparse
import json
import requests
import sys
from urllib.parse import urlencode

from whatsapp_utils import create_whatsapp_payload, format_json_response


def format_display_text(response):
    """Format response for display.

    Args:
        response: Response object from format_json_response

    Returns:
        str: Formatted text for display
    """
    if isinstance(response, str):
        return response

    # Format based on message type
    if response.get("type") == "interactive":
        interactive = response.get("interactive", {})
        text_parts = []

        # Add body text if present
        if interactive.get("body", {}).get("text"):
            text_parts.append(interactive["body"]["text"])

        # Add button text if present
        if interactive.get("action", {}).get("button"):
            text_parts.append(f"\n[Button: {interactive['action']['button']}]")

        # Add options if present
        if interactive.get("action", {}).get("sections"):
            for section in interactive["action"]["sections"]:
                if section.get("title"):
                    text_parts.append(f"\n{section['title']}:")
                for row in section.get("rows", []):
                    text_parts.append(f"- {row['title']}")

        return "\n".join(text_parts)
    elif response.get("type") == "text":
        return response.get("text", {}).get("body", "")
    else:
        return json.dumps(response, indent=2, ensure_ascii=False)


def send_message(args):
    """Send a message to the mock WhatsApp server."""
    payload = create_whatsapp_payload(
        args.phone, args.type, args.message, args.phone_number_id
    )

    # Add target to URL query params
    params = {'target': args.target}
    url = f"http://localhost:{args.port}/bot/webhook?{urlencode(params)}"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Mock-Testing": "true"
            },
            timeout=30
        )
        response.raise_for_status()

        print("Server Response:")
        formatted_response = format_json_response(response.text)
        display_text = format_display_text(formatted_response)
        print(display_text)

    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response text: {e.response.text}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Mock WhatsApp CLI Client - Send test messages to local or staging chatbot",
        epilog="""
Examples:
  # Text message
  %(prog)s "Hello, world!"

  # Menu option selection
  %(prog)s --type interactive "handleactionoffercredex"

  # Flow navigation
  %(prog)s --type interactive "flow:MAKE_SECURE_OFFER"

  # Button response
  %(prog)s --type button "accept_offer_123"
        """
    )
    parser.add_argument(
        "--phone",
        default="1234567890",
        help="Phone number (default: 1234567890)"
    )
    parser.add_argument(
        "--type",
        choices=["text", "button", "interactive"],
        default="text",
        help="""Message type (default: text). For interactive messages:
        - Menu options: Use the option ID directly (e.g., "handleactionoffercredex")
        - Flow navigation: Use "flow:SCREEN_NAME" format
        """
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
        "--target",
        choices=["local", "staging"],
        default="local",
        help="Target environment (default: local)"
    )
    parser.add_argument(
        "message",
        help="""Message to send. For interactive messages:
        - Menu options: The option ID (e.g., "handleactionoffercredex")
        - Flow navigation: "flow:SCREEN_NAME" (e.g., "flow:MAKE_SECURE_OFFER")
        """
    )

    args = parser.parse_args()
    send_message(args)


if __name__ == "__main__":
    main()
