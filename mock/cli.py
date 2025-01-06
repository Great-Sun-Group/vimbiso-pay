#!/usr/bin/env python3
"""Mock WhatsApp CLI client."""
import argparse
import json
import sys
from typing import Dict, Any
from urllib.parse import urlencode

import requests

from whatsapp_utils import (
    create_whatsapp_payload,
    extract_message_text,
    format_json_response
)


def format_display_text(response: Dict[str, Any]) -> str:
    """Format response for display."""
    if isinstance(response, str):
        return response

    # Extract message text
    message_text = extract_message_text(response)
    if message_text and isinstance(message_text, str):
        return message_text

    # Format interactive messages
    if response.get("type") == "interactive":
        interactive = response.get("interactive", {})
        text_parts = []

        # Add body text
        if interactive.get("body", {}).get("text"):
            text_parts.append(interactive["body"]["text"])

        # Add button/options
        action = interactive.get("action", {})
        if action.get("button"):
            text_parts.append(f"\n[Button: {action['button']}]")
        if action.get("sections"):
            for section in action["sections"]:
                if section.get("title"):
                    text_parts.append(f"\n{section['title']}:")
                for row in section.get("rows", []):
                    description = row.get("description", "")
                    text_parts.append(f"- {row['title']}" + (f" ({description})" if description else ""))

        return "\n".join(text_parts)

    # Format text messages
    if response.get("type") == "text":
        return response.get("text", {}).get("body", "")

    # Default to JSON string
    return json.dumps(response, indent=2, ensure_ascii=False)


def send_message(args: argparse.Namespace) -> None:
    """Send message to mock server."""
    # Parse message for list selections
    message = args.message
    if args.type == "list":
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            print("Error: List selection must be valid JSON")
            sys.exit(1)

    # Create WhatsApp-formatted payload
    whatsapp_payload = create_whatsapp_payload(
        phone_number=args.phone,
        message_type=args.type,
        message_text=message,
        phone_number_id=args.phone_number_id
    )

    # Add context for interactive messages
    if args.context_id:
        whatsapp_payload["entry"][0]["changes"][0]["value"]["messages"][0]["context"] = {
            "from": args.context_from or "15550783881",
            "id": args.context_id
        }

    # Send request
    params = {'target': args.target}
    url = f"http://localhost:{args.port}/bot/webhook?{urlencode(params)}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Mock-Testing": "true"
    }

    try:
        response = requests.post(
            url,
            json=whatsapp_payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        # Format and display response
        print("Server Response:")
        formatted_response = format_json_response(response.text)
        display_text = format_display_text(formatted_response)
        print(display_text)

    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response text: {e.response.text}")
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Mock WhatsApp CLI Client",
        epilog="""
Examples:
  # Text message
  %(prog)s "Hello, world!"

  # Menu option
  %(prog)s --type interactive "handleactionoffercredex"

  # Flow navigation
  %(prog)s --type interactive "flow:MAKE_SECURE_OFFER"

  # Button response
  %(prog)s --type button "accept_offer_123"

  # Form submission
  %(prog)s --type interactive "form:amount=100,recipientAccountHandle=@user123"

  # List selection
  %(prog)s --type list '{"id":"credex_offer","title":"Offer Secured Credex","description":"Create a new secured Credex offer"}' --context-id wamid.123 --context-from 15550783881
        """
    )

    parser.add_argument(
        "--phone",
        default="1234567890",
        help="Phone number (default: 1234567890)"
    )
    parser.add_argument(
        "--type",
        choices=["text", "button", "interactive", "list"],
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
        "--target",
        choices=["local", "staging"],
        default="local",
        help="Target environment (default: local)"
    )
    parser.add_argument(
        "--context-id",
        help="Message ID of the original message that triggered this interaction"
    )
    parser.add_argument(
        "--context-from",
        help="Phone number that sent the original message"
    )
    parser.add_argument(
        "message",
        help="Message to send"
    )

    args = parser.parse_args()
    send_message(args)


if __name__ == "__main__":
    main()
