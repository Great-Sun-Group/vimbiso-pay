"""Display handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.types import (
    ChannelIdentifier, InteractiveContent, InteractiveType,
    Message, MessageRecipient
)
from services.whatsapp.screens import format_account

logger = logging.getLogger(__name__)


def prepare_display_data(account: Dict, balance_data: Dict) -> Dict:
    """Prepare account display data"""
    return {
        "account": account.get("accountName", "Personal Account"),
        "handle": account.get("accountHandle", ""),
        "balances": {
            "secured": "\n".join(balance_data.get("securedNetBalancesByDenom", [])),
            "total": balance_data.get("netCredexAssetsInDefaultDenom", "")
        },
        "tier": account.get("tier_limit_display", "")
    }


def count_pending_offers(offers: Dict) -> Tuple[int, int]:
    """Count pending and outgoing offers"""
    pending_count = outgoing_count = 0
    for offer in offers.values():
        if offer.get("status") == "PENDING":
            if offer.get("isOutgoing", False):
                outgoing_count += 1
            else:
                pending_count += 1
    return pending_count, outgoing_count


def prepare_menu_options(pending_count: int, outgoing_count: int) -> Dict:
    """Prepare menu options with offer counts"""
    return {
        "button": "Options",
        "sections": [{
            "rows": [
                # Credex offer first
                {
                    "id": "credex_offer",
                    "title": "💰 Offer Secured Credex"
                },

                # Pending offer options if any
                *([] if pending_count == 0 else [
                    {
                        "id": "credex_accept",
                        "title": f"✅ Accept Offers ({pending_count})"
                    },
                    {
                        "id": "credex_decline",
                        "title": f"❌ Decline Offers ({pending_count})"
                    }
                ]),

                # Outgoing offer option if any
                *([] if outgoing_count == 0 else [
                    {
                        "id": "credex_cancel",
                        "title": f"🚫 Cancel Outgoing Offers ({outgoing_count})"
                    }
                ]),

                # Remaining base options
                {
                    "id": "transactions",
                    "title": "📊 View Transactions"
                },
                {
                    "id": "upgrade",
                    "title": "⭐ Upgrade Member Tier"
                }
            ]
        }]
    }


def handle_dashboard_display(state_manager: Any) -> Message:
    """Display dashboard with menu options"""
    # Let StateManager validate through state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "dashboard",
            "step": 0,
            "current_step": "display",
            "data": {}
        }
    })

    # Accessing personal_account triggers auth validation
    personal_account = state_manager.get("personal_account")
    balance_data = personal_account.get("balanceData", {})
    offers = personal_account.get("offerData", {}).get("offers", {})
    pending_count, outgoing_count = count_pending_offers(offers)

    # Update display data through state
    state_manager.update_state({
        "flow_data": {
            "data": {
                "display": prepare_display_data(personal_account, balance_data),
                "menu": prepare_menu_options(pending_count, outgoing_count)
            }
        }
    })

    # Get channel and display data through state
    channel = state_manager.get("channel")
    flow_data = state_manager.get("flow_data")

    # Return formatted message
    return Message(
        recipient=MessageRecipient(
            channel_id=ChannelIdentifier(
                channel=channel.get("type"),
                value=channel.get("identifier")
            )
        ),
        content=InteractiveContent(
            interactive_type=InteractiveType.LIST,
            body=format_account(flow_data.get("display")),
            action_items=flow_data.get("menu")
        )
    )


def handle_menu(state_manager: Any) -> Message:
    """Handle menu display"""
    # Let StateManager validate through state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": "menu",
            "step": 0,
            "current_step": "display",
            "data": {}
        }
    })

    # Let StateManager validate through state access
    return handle_dashboard_display(state_manager)


# Alias other handlers to menu handler
handle_hi = handle_menu
handle_refresh = handle_menu
