"""Authentication flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (ChannelIdentifier, ChannelType,
                                  InteractiveContent, InteractiveType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.credex.service import handle_login

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def handle_registration(state_manager: Any) -> Message:
    """Handle registration flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        channel = state_manager.get("channel")

        # Initialize registration flow through state update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "welcome",
                "data": {}
            }
        })

        # Return welcome message with registration button
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=InteractiveContent(
                interactive_type=InteractiveType.BUTTON,
                body="Welcome to VimbisoPay 💰\n\nWe're your portal 🚪to the credex ecosystem 🌱\n\nBecome a member 🌐 and open a free account 💳 to get started 📈",
                action_items={
                    "buttons": [{
                        "type": "reply",
                        "reply": {
                            "id": "start_registration",
                            "title": "Become a Member"
                        }
                    }]
                }
            )
        )

    except StateException as e:
        logger.error(f"Registration error: {str(e)}")
        # Update state with error
        state_manager.update_state({
            "flow_data": {
                "flow_type": "registration",
                "step": 0,
                "current_step": "error",
                "data": {
                    "error": str(e)
                }
            }
        })
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body="❌ Error: Unable to process registration. Please try again."
            ),
            metadata={
                "error": {
                    "type": "ERROR_VALIDATION",
                    "code": "REGISTRATION_ERROR",
                    "message": str(e)
                }
            }
        )


def attempt_login(state_manager: Any) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Attempt login enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Initialize auth flow through state update
        state_manager.update_state({
            "flow_data": {
                "flow_type": "auth",
                "step": 0,
                "current_step": "login",
                "data": {}
            }
        })

        # Attempt login
        success, response = handle_login(state_manager)
        if not success:
            return handle_login_error(response)

        data = response["data"]
        action = data["action"]
        details = action["details"]
        dashboard = data["dashboard"]
        accounts = dashboard["accounts"]

        # Find personal account
        personal_account = next(
            (account for account in accounts if account.get("accountType") == "PERSONAL"),
            None
        )
        if not personal_account:
            raise StateException("Personal account not found in response")

        # Extract member and account data
        member_data = dashboard.get("member", {})
        account_data = {
            "accountID": personal_account["accountID"],
            "accountName": personal_account["accountName"],
            "accountHandle": personal_account["accountHandle"],
            "balances": personal_account["balances"],
            "offerData": personal_account["offerData"]
        }

        # Single atomic update to maintain consistency
        state_manager.update_state({
            # 1. Auth state first
            "jwt_token": details["token"],
            "authenticated": True,

            # 2. Member data (including tier info)
            "member_id": details["memberID"],
            "tier_limit_display": member_data.get("tier_limit_display"),

            # 3. Account data
            "account_id": account_data["accountID"],
            "personal_account": account_data,

            # 4. Flow state last
            "flow_data": {
                "flow_type": "dashboard",
                "step": 0,
                "current_step": "display",
                "data": {}
            }
        })

        return True, None

    except (StateException, KeyError) as e:
        logger.error(f"Login error: {str(e)}")
        # Update state with error
        state_manager.update_state({
            "flow_data": {
                "flow_type": "auth",
                "step": 0,
                "current_step": "error",
                "data": {
                    "error": str(e)
                }
            }
        })
        return False, create_error_response("AUTH_ERROR", str(e))


def handle_login_error(response: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Handle login error"""
    try:
        error_data = response["data"]["action"]
        error_type = error_data["type"]
        error_code = error_data["details"]["code"]

        if error_type == "ERROR_NOT_FOUND" and error_code == "NOT_FOUND":
            return False, None

        if error_type == "ERROR_VALIDATION":
            return False, create_error_response("VALIDATION_ERROR", "Invalid login format")

        if error_type == "ERROR_INTERNAL":
            return False, create_error_response("SYSTEM_ERROR", "Service temporarily unavailable")

        return False, create_error_response(
            "AUTH_ERROR",
            response.get("message", "Authentication failed")
        )

    except KeyError:
        return False, create_error_response("AUTH_ERROR", "Invalid response format")


def create_error_response(code: str, message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "data": {
            "action": {
                "type": "ERROR_VALIDATION",
                "details": {
                    "code": code,
                    "message": message
                }
            }
        }
    }
