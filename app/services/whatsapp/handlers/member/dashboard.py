"""Dashboard handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import (
    ChannelIdentifier, InteractiveContent, InteractiveType, Message,
    MessageRecipient
)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.credex.member import get_member_accounts
from services.whatsapp.screens import format_account

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def get_menu_options(account: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get menu options for dashboard"""
    # Count pending and outgoing offers if available
    pending_offers = 0
    outgoing_offers = 0
    if account and "offerData" in account:
        offers = account["offerData"].get("offers", [])
        for offer in offers:
            if offer.get("status") == "PENDING":
                if offer.get("isOutgoing"):
                    outgoing_offers += 1
                else:
                    pending_offers += 1

    # Base menu options always available
    menu_options = [
        {
            "id": "offer",
            "title": "💰 Offer Secured Credex"
        },
        {
            "id": "transactions",
            "title": "📊 View Transactions"
        },
        {
            "id": "upgrade",
            "title": "⭐ Upgrade Member Tier"
        }
    ]

    # Add offer-related options if there are pending offers
    if pending_offers > 0:
        menu_options.insert(1, {
            "id": "accept",
            "title": f"✅ Accept Offers ({pending_offers})"
        })
        menu_options.insert(2, {
            "id": "decline",
            "title": f"❌ Decline Offers ({pending_offers})"
        })

    if outgoing_offers > 0:
        menu_options.insert(3, {
            "id": "cancel",
            "title": f"🚫 Cancel Outgoing Offers ({outgoing_offers})"
        })

    return {
        "button": "Options",
        "sections": [
            {
                "rows": menu_options
            }
        ]
    }


def handle_dashboard_display(state_manager: Any) -> Message:
    """Handle dashboard display enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get account data
        success, result = get_member_accounts(state_manager)
        if not success:
            raise StateException("Failed to get account details")

        # Get account data (StateManager validates structure)
        account = result["data"]["accounts"][0]  # We know there's only personal account

        # Update flow data with account info
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "dashboard",
                "step": 0,
                "current_step": "display",
                "data": {
                    "account": account
                }
            }
        })
        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        if not flow_data or not flow_data.get("data"):
            raise StateException("Missing flow data")

        # Format account data
        account_data = flow_data["data"]["account"]
        balance_data = account_data.get("balanceData", {})
        secured_balances = balance_data.get("securedNetBalancesByDenom", [])
        formatted_account = {
            "account": account_data.get("accountName", "Personal Account"),
            "handle": account_data.get("accountHandle", ""),
            "securedNetBalancesByDenom": "\n".join(secured_balances) if secured_balances else "",
            "netCredexAssetsInDefaultDenom": balance_data.get("netCredexAssetsInDefaultDenom", ""),
            "tier_limit_display": account_data.get("tier_limit_display", "")
        }

        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=channel["type"],
                    value=channel["identifier"]
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body=format_account(formatted_account),
                action_items=get_menu_options(account_data)
            )
        )

    except StateException as e:
        logger.error(f"Dashboard error: {str(e)}")
        # Get channel for error message
        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=channel["type"],
                    value=channel["identifier"]
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body="❌ Error: Unable to load dashboard. Please try again.",
                action_items=get_menu_options()
            )
        )
