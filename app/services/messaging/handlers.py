"""Message handlers for different contexts

This module handles message formatting and sending for different contexts.
The flow routing is handled by core/messaging/flow.py.
"""

import logging
from typing import Any, Dict

from core.messaging.formatters import AccountFormatters
from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Button, Message, TextContent

from .utils import get_recipient

logger = logging.getLogger(__name__)


def handle_dashboard_display(messaging_service: MessagingServiceInterface, state_manager: Any, verified_data: Dict) -> Message:
    """Format and send dashboard display message"""
    # Format message using account data
    active_account = verified_data["active_account"]
    balance_data = active_account.get("balanceData", {})

    # Get member tier from dashboard data
    member_data = verified_data["dashboard"].get("member", {})
    member_tier = member_data.get("memberTier")
    account_data = {
        "accountName": active_account.get("accountName"),
        "accountHandle": active_account.get("accountHandle"),
        "netCredexAssetsInDefaultDenom": balance_data.get('netCredexAssetsInDefaultDenom', '0.00'),
        "defaultDenom": member_data.get('defaultDenom', 'USD'),
        **balance_data
    }

    # Only include tier limit for tier < 2
    if member_tier < 2:
        account_data["tier_limit_raw"] = member_data.get("remainingAvailableUSD", "0.00")
    message = AccountFormatters.format_dashboard(account_data)

    # Get recipient for message
    recipient = get_recipient(state_manager)

    # Check if we should use list format
    if verified_data.get("use_list"):
        # Use WhatsApp's list message format
        return messaging_service.send_interactive(
            recipient=recipient,
            body=message,
            sections=verified_data["sections"],
            button_text=verified_data.get("button_text", "Select Option")
        )
    else:
        # Check if buttons are provided
        if "buttons" in verified_data:
            # Convert button dictionaries to Button objects (max 3 for WhatsApp)
            buttons = [
                Button(id=btn["id"], title=btn["title"])
                for btn in verified_data["buttons"][:3]  # Limit to first 3 buttons
            ]
            # Use button format for simple yes/no interactions
            return messaging_service.send_interactive(
                recipient=recipient,
                body=message,
                buttons=buttons
            )
        else:
            # Fallback to simple text message
            return Message(
                recipient=recipient,
                content=TextContent(body=message)
            )


def handle_rate_limit_error(state_manager: Any) -> Message:
    """Format and send rate limit error message"""
    return Message(
        recipient=get_recipient(state_manager),
        content=TextContent(
            body="⚠️ Too many messages sent. Please wait a moment before trying again."
        )
    )


def handle_greeting(state_manager: Any, content: str) -> Message:
    """Format and send greeting message"""
    return Message(
        recipient=get_recipient(state_manager),
        content=TextContent(body=content)
    )


def handle_error(state_manager: Any, error: str) -> Message:
    """Format and send error message"""
    return Message(
        recipient=get_recipient(state_manager),
        content=TextContent(body=f"⚠️ {error}")
    )
