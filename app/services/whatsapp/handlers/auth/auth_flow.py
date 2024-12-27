"""Authentication flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from services.credex.service import handle_login

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def handle_registration(state_manager: Any) -> Message:
    """Handle registration flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate channel info before access
        channel = state_manager.get("channel")
        if not channel or "identifier" not in channel:
            raise StateException("Invalid channel information")

        if state_manager.get("flow_action") == "register":
            logger.info("Starting registration")
            return Message(
                recipient=MessageRecipient(
                    member_id="pending",
                    channel_id=ChannelIdentifier(
                        channel=ChannelType.WHATSAPP,
                        value=channel["identifier"]
                    )
                ),
                content=TextContent(
                    body="Welcome to VimbisoPay 💰\n\nWe're your portal 🚪to the credex ecosystem 🌱\n\nBecome a member 🌐 and open a free account 💳 to get started 📈"
                )
            )

        return handle_action_menu(state_manager)

    except StateException as e:
        logger.error(f"Registration error: {str(e)}")
        return Message(
            recipient=MessageRecipient(
                member_id="pending",
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
        # Validate required state before proceeding
        if not state_manager.get("channel"):
            raise StateException("Channel information missing")

        # Attempt login with validated state
        success, response = handle_login(state_manager)
        if not success:
            return handle_login_error(response)

        # Validate login response structure
        if not isinstance(response, dict) or "data" not in response:
            raise StateException("Invalid login response format")

        data = response["data"]
        if "action" not in data or "dashboard" not in data:
            raise StateException("Missing required login response sections")

        # Extract and validate required fields
        action = data["action"]
        if "details" not in action:
            raise StateException("Missing action details in response")

        details = action["details"]
        member_id = details.get("memberID")
        token = details.get("token")
        if not member_id or not token:
            raise StateException("Missing required authentication data")

        # Validate and extract account information
        dashboard = data["dashboard"]
        if "accounts" not in dashboard:
            raise StateException("Account information missing")

        accounts = dashboard["accounts"]
        personal_account = next(
            (account for account in accounts if account.get("accountType") == "PERSONAL"),
            None
        )
        if not personal_account or "accountID" not in personal_account:
            raise StateException("Personal account not found")

        # Update state with validated data
        new_state = {
            "member_id": member_id,
            "jwt_token": token,
            "authenticated": True,
            "account_id": personal_account["accountID"],
            "personal_account": personal_account,  # Store only personal account data
            "flow_data": {
                "id": "user_state",
                "flow_type": "auth",
                "step": 0
            }
        }

        success, error = state_manager.update_state(new_state)
        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Return only success flag and None since state is already updated
        return True, None

    except StateException as e:
        logger.error(f"Login error: {str(e)}")
        return False, create_error_response("AUTH_ERROR", str(e))


def handle_login_error(response: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Handle login error with proper validation"""
    if not isinstance(response, dict) or "data" not in response:
        return False, create_error_response("AUTH_ERROR", "Invalid response format")

    error_data = response["data"].get("action", {})
    error_type = error_data.get("type")
    error_code = error_data.get("details", {}).get("code")

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


def handle_action_menu(state_manager: Any) -> Message:
    """Handle menu action with proper state validation"""
    try:
        # Validate channel info before access
        channel = state_manager.get("channel")
        if not channel or "identifier" not in channel:
            raise StateException("Invalid channel information")

        return Message(
            recipient=MessageRecipient(
                member_id=state_manager.get("member_id") or "pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Please select an action:\n\n1. View Dashboard\n2. Make Payment\n3. View History\n4. Settings"
            )
        )

    except StateException as e:
        logger.error(f"Menu display error: {str(e)}")
        return Message(
            recipient=MessageRecipient(
                member_id="pending",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body="❌ Error: Unable to display menu. Please try again."
            ),
            metadata={
                "error": {
                    "type": "ERROR_VALIDATION",
                    "code": "MENU_ERROR",
                    "message": str(e)
                }
            }
        )
