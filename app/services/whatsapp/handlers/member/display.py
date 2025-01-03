"""Display handler enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.types import (ChannelIdentifier, InteractiveContent,
                                  InteractiveType, Message, MessageRecipient,
                                  TextContent)
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException
from services.whatsapp.screens import format_account

logger = logging.getLogger(__name__)


def prepare_display_data(account: Dict, member_data: Dict) -> Dict:
    """Prepare account display data"""
    # Format tier limit if available (n/a for tier >= 3)
    tier_display = ""
    if member_data["memberTier"] < 3 and member_data.get("remainingAvailableUSD") is not None:
        tier_name = "OPEN" if member_data["memberTier"] == 1 else "VERIFIED"
        tier_display = f"DAILY {tier_name} TIER LIMIT: {member_data['remainingAvailableUSD']} USD"

    return {
        "account": account["accountName"],
        "handle": account["accountHandle"],
        "securedNetBalancesByDenom": "\n".join(account["balanceData"]["securedNetBalancesByDenom"]),
        "netCredexAssetsInDefaultDenom": account["balanceData"]["netCredexAssetsInDefaultDenom"],
        "tier_limit_display": tier_display
    }


def count_pending_offers(account: Dict) -> Tuple[int, int]:
    """Count pending and outgoing offers"""
    # pendingInData and pendingOutData are arrays from API
    pending_count = len(account.get("pendingInData", []))
    outgoing_count = len(account.get("pendingOutData", []))
    return pending_count, outgoing_count


def prepare_menu_options(pending_count: int, outgoing_count: int) -> Dict:
    """Prepare menu options with offer counts"""
    return {
        "button": "Options",
        "sections": [{
            "rows": [
                # Offer secured first
                {
                    "id": "offer",
                    "title": "💰 Offer Secured Credex"
                },

                # Pending offer options if any
                *([] if pending_count == 0 else [
                    {
                        "id": "accept",
                        "title": f"✅ Accept Offers ({pending_count})"
                    },
                    {
                        "id": "decline",
                        "title": f"❌ Decline Offers ({pending_count})"
                    }
                ]),

                # Outgoing offer option if any
                *([] if outgoing_count == 0 else [
                    {
                        "id": "cancel",
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
    try:
        # Validate state manager
        if not state_manager:
            raise ComponentException(
                message="State manager is required",
                component="dashboard",
                field="state_manager",
                value="None"
            )

        # Get required state data
        channel = state_manager.get("channel")
        accounts = state_manager.get("accounts")
        active_id = state_manager.get("active_account_id")
        member_data = state_manager.get("member_data")

        # Validate required data
        if not all([channel, accounts, active_id, member_data]):
            raise FlowException(
                message="Missing required state data",
                step="dashboard",
                action="display",
                data={
                    "channel": bool(channel),
                    "accounts": bool(accounts),
                    "active_id": bool(active_id),
                    "member_data": bool(member_data)
                }
            )

        # Get active account
        try:
            active_account = next(
                account for account in accounts
                if account["accountID"] == active_id
            )
        except StopIteration:
            raise FlowException(
                message="Active account not found",
                step="dashboard",
                action="get_account",
                data={"active_id": active_id}
            )

        # Prepare display data
        display_data = prepare_display_data(active_account, member_data)

        # Return dashboard message
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=channel["type"],
                    value=channel["identifier"]
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body=format_account(display_data),
                action_items=prepare_menu_options(
                    *count_pending_offers(active_account)
                )
            )
        )

    except ComponentException as e:
        # Handle component validation errors
        logger.error("Dashboard validation error", extra={
            "component": e.component,
            "field": e.field,
            "value": e.value
        })
        error = ErrorHandler.handle_component_error(
            component=e.component,
            field=e.field,
            value=e.value,
            message=str(e)
        )
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=state_manager.get("channel")["type"],
                    value=state_manager.get_channel_id()
                )
            ),
            content=TextContent(error["message"]),
            metadata={"error": error}
        )

    except FlowException as e:
        # Handle flow errors
        logger.error("Dashboard flow error", extra={
            "step": e.step,
            "action": e.action,
            "data": e.data
        })
        error = ErrorHandler.handle_flow_error(
            step=e.step,
            action=e.action,
            data=e.data,
            message=str(e)
        )
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=state_manager.get("channel")["type"],
                    value=state_manager.get_channel_id()
                )
            ),
            content=TextContent(error["message"]),
            metadata={"error": error}
        )

    except Exception:
        # Handle unexpected errors
        logger.error("Dashboard error", extra={
            "state": {
                "channel": bool(state_manager.get("channel")),
                "accounts": bool(state_manager.get("accounts")),
                "active_id": bool(state_manager.get("active_account_id")),
                "member_data": bool(state_manager.get("member_data"))
            }
        })
        error = ErrorHandler.handle_system_error(
            code="DISPLAY_ERROR",
            service="dashboard",
            action="display",
            message=ErrorHandler.MESSAGES["system"]["service_error"]
        )
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=state_manager.get("channel")["type"],
                    value=state_manager.get_channel_id()
                )
            ),
            content=TextContent(error["message"]),
            metadata={"error": error}
        )
