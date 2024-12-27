"""Profile and state management"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)


def _get_action_message(action: Dict[str, Any], action_type: str) -> str:
    """Get action message from response"""
    # Return explicit message if present
    if action.get("message"):
        return action["message"]

    # Check details for message
    if action.get("details", {}).get("message"):
        return action["details"]["message"]

    return ""


def _structure_profile_data(
    api_response: dict,
    state_manager: Any,
    action_type: str = "update"
) -> dict:
    """Structure API response into proper profile format"""
    data = api_response.get("data", {})
    dashboard = data.get("dashboard", {})
    action = data.get("action", {})

    # Validate channel info at boundary
    validation = StateValidator.validate_before_access(
        {"channel": state_manager.get("channel")},
        {"channel"}
    )
    if not validation.is_valid:
        logger.error(f"Invalid state: {validation.error_message}")
        return {}

    channel = state_manager.get("channel", {})

    return {
        "action": {
            "id": action.get("id", ""),
            "type": action.get("type", action_type),
            "timestamp": datetime.now().isoformat(),
            "actor": channel.get("identifier"),
            "details": action.get("details", {}),
            "message": _get_action_message(action, action_type),
            "status": action.get("status", "")
        },
        "dashboard": dashboard
    }


def _handle_account_setup(
    dashboard_data: Dict[str, Any],
    state_manager: Any
) -> None:
    """Handle account setup in state"""
    # Get and validate accounts data
    accounts = dashboard_data.get("accounts", [])
    if not isinstance(accounts, list):
        logger.warning("Invalid accounts data format")
        return

    try:
        # Process accounts data
        processed_accounts = []
        for account in accounts:
            if isinstance(account, dict):
                # Handle nested account data structure
                if account.get("success") and isinstance(account.get("data"), dict):
                    processed_account = account["data"]
                else:
                    processed_account = account

                # Ensure account has required fields
                if isinstance(processed_account, dict) and all(
                    isinstance(processed_account.get(field), str)
                    for field in ["accountType", "accountHandle"]
                ):
                    processed_accounts.append(processed_account)

        # Find personal account with proper validation
        personal_account = None
        channel = state_manager.get("channel", {})
        channel_identifier = channel.get("identifier")

        for account in processed_accounts:
            if account["accountType"] == "PERSONAL":
                personal_account = account
                break
            elif account["accountHandle"] == channel_identifier:
                personal_account = account

        # Update state with validated account
        if personal_account:
            success, error = state_manager.update_state({"current_account": personal_account})
            if not success:
                raise ValueError(f"Failed to update current account: {error}")
            logger.info(f"Successfully set default account: {personal_account['accountHandle']}")
        else:
            logger.warning("No valid personal account found")

    except Exception as e:
        logger.error(f"Error in account setup: {str(e)}")


def update_profile_from_response(
    api_response: Dict[str, Any],
    state_manager: Any,
    action_type: str,
    update_from: str,
    token: Optional[str] = None
) -> None:
    """Update profile and state from API response"""
    try:
        # Validate api_response
        if not isinstance(api_response, dict):
            logger.error("Invalid API response format")
            api_response = {}

        # Structure profile data
        profile_data = _structure_profile_data(api_response, state_manager, action_type)

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "profile": state_manager.get("profile"),
                "current_account": state_manager.get("current_account")
            },
            {"profile", "current_account"}
        )
        if not validation.is_valid:
            logger.error(f"Invalid state: {validation.error_message}")
            return

        # Update state
        updates = {"profile": profile_data}

        # Add token if provided
        if token:
            updates["jwt_token"] = token

        # Update state with new profile
        success, error = state_manager.update_state(updates)
        if not success:
            raise ValueError(f"Failed to update state: {error}")

        # Handle account setup if dashboard data present
        dashboard_data = api_response.get("data", {}).get("dashboard")
        if dashboard_data:
            _handle_account_setup(dashboard_data, state_manager)

        logger.info(f"State updated from {update_from}")

    except Exception as e:
        logger.error(f"Error updating profile from response: {str(e)}")
        raise


def handle_successful_refresh(
    member_info: Dict[str, Any],
    state_manager: Any
) -> Optional[str]:
    """Handle successful member info refresh"""
    try:
        # Validate member_info structure
        if not isinstance(member_info, dict):
            logger.error("Invalid member_info format")
            return "Invalid member info format"

        # Extract and validate dashboard data
        data = member_info.get("data", {})
        dashboard_data = data.get("dashboard")
        if not dashboard_data:
            logger.error("Missing required dashboard data")
            return "Missing dashboard data"

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"profile": state_manager.get("profile")},
            {"profile"}
        )
        if not validation.is_valid:
            logger.error(f"Invalid state: {validation.error_message}")
            return validation.error_message

        # Get current profile action
        current_profile = state_manager.get("profile", {})
        current_action = current_profile.get("action", {})

        # Add current state's action data to member info to preserve it
        if "data" not in member_info:
            member_info["data"] = {}
        if "action" not in member_info["data"]:
            member_info["data"]["action"] = {}

        # Preserve existing action data while keeping any new action data
        existing_action = member_info["data"]["action"]
        member_info["data"]["action"].update({
            "id": existing_action.get("id", current_action.get("id", "")),
            "message": current_action.get("message", ""),
            "status": current_action.get("status", ""),
            "type": current_action.get("type", "refresh"),
            "details": existing_action.get("details", current_action.get("details", {}))
        })

        # Structure profile data
        profile_data = _structure_profile_data(member_info, state_manager, "refresh")
        profile_data["dashboard"] = dashboard_data

        # Update state with new profile data
        success, error = state_manager.update_state({"profile": profile_data})
        if not success:
            raise ValueError(f"Failed to update profile: {error}")

        # Handle account setup
        _handle_account_setup(dashboard_data, state_manager)

        logger.info("State updated successfully after refresh")
        return None

    except Exception as e:
        logger.error(f"Error handling refresh: {str(e)}")
        return str(e)
