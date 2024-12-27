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
        channel = state_manager.get("channel")

        if state_manager.get("flow_action") == "register":
            logger.info("Starting registration")
            return Message(
                recipient=MessageRecipient(
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
        # StateManager validates channel exists
        state_manager.get("channel")

        # Attempt login
        success, response = handle_login(state_manager)
        if not success:
            return handle_login_error(response)

        data = response["data"]
        action = data["action"]
        details = action["details"]
        dashboard = data["dashboard"]
        accounts = dashboard["accounts"]

        personal_account = next(
            (account for account in accounts if account.get("accountType") == "PERSONAL"),
            None
        )

        # Update state - StateManager validates structure
        new_state = {
            "member_id": details["memberID"],
            "jwt_token": details["token"],
            "authenticated": True,
            "account_id": personal_account["accountID"],
            "personal_account": personal_account,
            "flow_data": {
                "flow_type": "auth",
                "step": 0,
                "current_step": "authenticated"
            }
        }

        success, error = state_manager.update_state(new_state)
        if not success:
            raise StateException(f"Failed to update state: {error}")

        return True, None

    except (StateException, KeyError) as e:
        logger.error(f"Login error: {str(e)}")
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


def handle_action_menu(state_manager: Any) -> Message:
    """Handle menu action"""
    try:
        channel = state_manager.get("channel")

        return Message(
            recipient=MessageRecipient(
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
