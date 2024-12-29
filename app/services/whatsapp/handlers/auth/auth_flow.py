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

        # Check for error response (has empty dashboard)
        action_type = response["data"]["action"]["type"]
        if action_type.startswith("ERROR_"):
            return handle_login_error({
                "message": response["data"]["action"]["details"].get("reason", "Login failed")
            })

        # Get accounts from dashboard
        dashboard = response["data"]["dashboard"]
        raw_accounts = dashboard["accounts"]
        accounts = []
        for account in raw_accounts:
            # Keep exact API structure
            accounts.append({
                "accountID": account["accountID"],
                "accountName": account["accountName"],
                "accountHandle": account["accountHandle"],
                "accountType": account["accountType"],
                "defaultDenom": account["defaultDenom"],
                "isOwnedAccount": account["isOwnedAccount"],
                "sendOffersTo": account.get("sendOffersTo"),
                "balanceData": account["balanceData"],
                "pendingInData": account.get("pendingInData", []),
                "pendingOutData": account.get("pendingOutData", [])
            })

        # Find personal account ID
        active_account_id = next(
            account["accountID"]
            for account in accounts
            if account["accountType"] == "PERSONAL"
        )

        # Get member data from dashboard
        dashboard = response["data"]["dashboard"]
        member_data = {
            "memberTier": dashboard["memberTier"],
            "remainingAvailableUSD": dashboard.get("remainingAvailableUSD"),
            "firstname": dashboard["firstname"],
            "lastname": dashboard["lastname"],
            "memberHandle": dashboard["memberHandle"],
            "defaultDenom": dashboard["defaultDenom"]
        }

        # Let StateManager validate through state update
        success, error = state_manager.update_state({
            # Core identity - SINGLE SOURCE OF TRUTH
            "jwt_token": response["data"]["action"]["details"]["token"],
            "authenticated": True,
            "member_id": response["data"]["action"]["details"]["memberID"],

            # Member data at top level
            "member_data": member_data,

            # Account data at top level for future account switching
            "accounts": accounts,
            "active_account_id": active_account_id,

            # Flow state only for routing
            "flow_data": {
                "flow_type": "dashboard",
                "step": 0,
                "current_step": "display"
            }
        })

        if not success:
            raise StateException(f"Failed to update auth state: {error}")

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
    """Handle login error through state validation"""
    # Let StateManager validate error response structure
    return False, {
        "data": {
            "action": {
                "type": "ERROR_VALIDATION",
                "details": {
                    "code": "AUTH_ERROR",
                    "message": response.get("message", "Authentication failed")
                }
            }
        }
    }


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
