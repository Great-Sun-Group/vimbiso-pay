"""Dashboard flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...screens import format_account

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def get_menu_options(include_all: bool = True) -> Dict[str, Any]:
    """Get menu options for dashboard"""
    if include_all:
        return {
            "button": "Options",
            "sections": [
                {
                    "title": "Account Options",
                    "rows": [
                        {
                            "id": "refresh",
                            "title": "🔄 Refresh Dashboard"
                        },
                        {
                            "id": "offers",
                            "title": "💰 View Offers"
                        },
                        {
                            "id": "transactions",
                            "title": "📊 View Transactions"
                        }
                    ]
                }
            ]
        }
    return {
        "button": "Options",
        "sections": [
            {
                "title": "Available Actions",
                "rows": [
                    {
                        "id": "refresh",
                        "title": "🔄 Try Again"
                    }
                ]
            }
        ]
    }


def get_account_details(state_manager: Any, credex_service: Any) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """Get account details enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "member_id": state_manager.get("member_id"),
                "account_id": state_manager.get("account_id")
            },
            {"member_id", "account_id"}
        )
        if not validation.is_valid:
            return False, {}, validation.error_message

        # Get required data
        member_id = state_manager.get("member_id")
        account_id = state_manager.get("account_id")

        # Get account details from CredEx service
        success, account_data = credex_service.get_member_accounts(member_id)
        if not success:
            error_msg = account_data.get("message", "Failed to get account details")
            logger.error(f"API call failed: {error_msg}")
            return False, {}, error_msg

        # Validate account data
        if not isinstance(account_data, dict) or "accounts" not in account_data:
            return False, {}, "Invalid account data format"

        # Find personal account
        personal_account = next(
            (account for account in account_data["accounts"]
             if account.get("accountID") == account_id),
            None
        )
        if not personal_account:
            return False, {}, "Account not found"

        # Format account info
        account_info = {
            "account": personal_account.get("name", "Personal Account"),
            "handle": personal_account.get("handle", "Not Available"),
            "securedNetBalancesByDenom": personal_account.get("securedNetBalancesByDenom", ""),
            "netCredexAssetsInDefaultDenom": personal_account.get("netCredexAssetsInDefaultDenom", ""),
            "tier_limit_display": personal_account.get("tierLimitDisplay", "")
        }

        return True, account_info, None

    except Exception as e:
        logger.error(f"Error getting account details: {str(e)}")
        return False, {}, str(e)


def handle_dashboard_display(
    state_manager: Any,
    credex_service: Any,
    success_message: Optional[str] = None,
    flow_type: str = "dashboard"
) -> Message:
    """Handle dashboard display enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        credex_service: CredEx service instance
        success_message: Optional message to display
        flow_type: Flow type identifier

    Returns:
        Message: Dashboard display message
    """
    try:
        # Validate flow type
        if flow_type not in {"dashboard", "refresh", "offers", "transactions"}:
            raise ValueError("Invalid flow type")

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id"),
                "account_id": state_manager.get("account_id"),
                "authenticated": state_manager.get("authenticated"),
                "jwt_token": state_manager.get("jwt_token")
            },
            {"channel", "member_id", "account_id", "authenticated", "jwt_token"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required data
        channel = state_manager.get("channel")
        member_id = state_manager.get("member_id")

        # Log dashboard fetch attempt
        logger.info(f"Fetching dashboard data for channel {channel['identifier']}")

        # Get account details
        success, account_info, error = get_account_details(state_manager, credex_service)
        if not success:
            raise ValueError(error)

        # Create dashboard text
        dashboard_text = format_account(account_info)

        # Add success message if provided
        if success_message:
            dashboard_text = f"{success_message}\n\n{dashboard_text}"

        # Log success
        audit.log_flow_event(
            "dashboard_flow",
            "complete",
            None,
            {
                "flow_type": flow_type,
                "channel_id": channel["identifier"],
                "member_id": member_id
            },
            "success"
        )

        # Return formatted message
        return Message(
            recipient=MessageRecipient(
                member_id=member_id,
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body=dashboard_text,
                action_items=get_menu_options(True)
            )
        )

    except ValueError as e:
        # Get channel info for error logging
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error logging: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Dashboard error: {str(e)} for channel {channel_id}")

        # Return error message
        return Message(
            recipient=MessageRecipient(
                member_id="unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel_id
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.LIST,
                body="❌ Error: Unable to load dashboard. Please try again.",
                action_items=get_menu_options(False)
            )
        )
