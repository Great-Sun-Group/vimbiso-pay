"""Dashboard handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import (ChannelIdentifier, ChannelType, InteractiveContent,
                                  InteractiveType, Message, MessageRecipient)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.credex.member import get_member_accounts
from services.whatsapp.screens import format_account

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def get_menu_options(error: bool = False, account: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get menu options for dashboard"""
    if error:
        return {
            "button": "Options",
            "sections": [
                {
                    "rows": [
                        {
                            "id": "refresh",
                            "title": "🔄 Try Again"
                        }
                    ]
                }
            ]
        }

    # Count pending and outgoing offers from account data
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

    return {
        "button": "Options",
        "sections": [
            {
                "rows": [
                    {
                        "id": "offer",
                        "title": "💰 Offer Secured Credex"
                    },
                    {
                        "id": "accept",
                        "title": f"✅ Accept Offers ({pending_offers})"
                    },
                    {
                        "id": "decline",
                        "title": f"❌ Decline Offers ({pending_offers})"
                    },
                    {
                        "id": "cancel",
                        "title": f"🚫 Cancel Outgoing Offers ({outgoing_offers})"
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
            }
        ]
    }


def handle_dashboard_display(state_manager: Any) -> Message:
    """Handle dashboard display enforcing SINGLE SOURCE OF TRUTH"""
    error = False
    try:
        # Get account data and update state
        success, result = get_member_accounts(state_manager)
        if not success:
            raise StateException("Failed to get account details")

        # Validate response structure
        if not isinstance(result, dict) or "data" not in result or "accounts" not in result["data"]:
            raise StateException("Invalid account data format")

        # Extract and validate account data
        account = result["data"]["accounts"][0]  # We know there's only personal account
        if not isinstance(account, dict):
            raise StateException("Invalid account format")

        # Format and store account data in state
        balance_data = account.get("balanceData", {})
        secured_balances = balance_data.get("securedNetBalancesByDenom", [])
        formatted_account = {
            "account": account.get("accountName", "Personal Account"),
            "handle": account.get("accountHandle", ""),
            "securedNetBalancesByDenom": "\n".join(secured_balances) if secured_balances else "",
            "netCredexAssetsInDefaultDenom": balance_data.get("netCredexAssetsInDefaultDenom", ""),
            "tier_limit_display": account.get("tier_limit_display", "")
        }

        # Update state with formatted account data
        success, error_msg = state_manager.update_state({
            "formatted_account": formatted_account,
            "account_data": account  # Store raw account data for other operations
        })
        if not success:
            raise StateException(f"Failed to update state: {error_msg}")
    except StateException as e:
        logger.error(f"Dashboard error: {str(e)}")
        error = True
        # Update state to reflect error
        state_manager.update_state({"dashboard_error": str(e)})

    try:
        # Get required data from state
        channel_info = state_manager.get("channel")
        if not channel_info or "type" not in channel_info or "identifier" not in channel_info:
            raise StateException("Invalid channel information")

        # Get account data from state
        account = state_manager.get("account_data") if not error else None
        formatted_account = state_manager.get("formatted_account") if not error else None

        return Message(
            recipient=MessageRecipient(
                member_id=state_manager.get("member_id"),
                channel_id=ChannelIdentifier(
                    channel=channel_info["type"],
                    value=channel_info["identifier"]
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body="❌ Error: Unable to load dashboard. Please try again." if error else format_account(formatted_account),
                action_items=get_menu_options(error, account)
            )
        )

    except StateException as e:
        logger.error(f"Message creation error: {str(e)}")
        # Return basic error message if we can't create proper message
        return Message(
            recipient=MessageRecipient(
                member_id=state_manager.get("member_id") or "unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body="❌ Critical Error: System temporarily unavailable",
                action_items=get_menu_options(error=True)
            )
        )
