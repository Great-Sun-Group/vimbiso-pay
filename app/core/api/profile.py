"""Profile and state management"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.utils.state_validator import StateValidator
from ..config.constants import CachedUser
from .base import BaseAPIClient

logger = logging.getLogger(__name__)


class ProfileManager(BaseAPIClient):
    """Handles profile data structuring and state management"""

    def _get_action_message(self, action: Dict[str, Any], action_type: str) -> str:
        """Get action message from response"""
        # Return explicit message if present
        if action.get("message"):
            return action["message"]

        # Check details for message
        if action.get("details", {}).get("message"):
            return action["details"]["message"]

        return ""

    def _structure_profile_data(
        self,
        api_response: dict,
        action_type: str = "update"
    ) -> dict:
        """Structure API response into proper profile format"""
        data = api_response.get("data", {})
        dashboard = data.get("dashboard", {})
        action = data.get("action", {})

        return {
            "action": {
                "id": action.get("id", ""),
                "type": action.get("type", action_type),
                "timestamp": datetime.now().isoformat(),
                "actor": self.bot_service.user.state_manager.get("channel", {}).get("identifier"),
                "details": action.get("details", {}),
                "message": self._get_action_message(action, action_type),
                "status": action.get("status", "")
            },
            "dashboard": dashboard
        }

    def _update_state_with_profile(
        self,
        profile_data: Dict[str, Any],
        current_state: Dict[str, Any],
        update_from: str
    ) -> None:
        """Update state with new profile data"""
        # Validate current_state is a dictionary
        if not isinstance(current_state, dict):
            logger.error("Invalid current_state format")
            current_state = {}

        # Ensure profile_data is a dictionary
        if not isinstance(profile_data, dict):
            logger.error("Invalid profile_data format")
            profile_data = {
                "action": {
                    "id": "",
                    "type": "",
                    "timestamp": datetime.now().isoformat(),
                    "actor": self.bot_service.user.state_manager.get("channel", {}).get("identifier"),
                    "details": {}
                },
                "dashboard": {}
            }

        channel_identifier = self.bot_service.user.state_manager.get("channel", {}).get("identifier")
        user = CachedUser(channel_identifier)

        # Update profile in state with validation
        current_state["profile"] = profile_data

        # Ensure current_account is a dictionary
        if not isinstance(current_state.get("current_account"), dict):
            current_state["current_account"] = {}

        # Update state
        user.state.update_state(current_state)
        logger.info(f"State updated from {update_from}")

    def _handle_account_setup(
        self,
        dashboard_data: Dict[str, Any],
        current_state: Dict[str, Any]
    ) -> None:
        """Handle account setup in state"""
        # Initialize current_account as empty dict if not present or invalid
        if not isinstance(current_state.get("current_account"), dict):
            current_state["current_account"] = {}

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
            channel_identifier = self.bot_service.user.state_manager.get("channel", {}).get("identifier")
            for account in processed_accounts:
                if account["accountType"] == "PERSONAL":
                    personal_account = account
                    break
                elif account["accountHandle"] == channel_identifier:
                    personal_account = account

            # Update state with validated account
            if personal_account:
                current_state["current_account"] = personal_account
                logger.info(f"Successfully set default account: {personal_account['accountHandle']}")
            else:
                logger.warning("No valid personal account found")

        except Exception as e:
            logger.error(f"Error in account setup: {str(e)}")

    def _get_required_state(self) -> Dict[str, Any]:
        """Get required state fields with validation at boundary"""
        # Get required fields
        required_fields = {"profile", "current_account", "jwt_token", "authenticated"}
        state = {
            field: self.bot_service.user.state_manager.get(field)
            for field in required_fields
        }

        # Validate at boundary
        validation = StateValidator.validate_state(state)
        if not validation.is_valid:
            logger.warning("Invalid state format, initializing new state")
            state = {
                "profile": {
                    "action": {
                        "id": "",
                        "type": "",
                        "timestamp": "",
                        "actor": "",
                        "details": {}
                    },
                    "dashboard": {
                        "member": {},
                        "accounts": []
                    }
                },
                "current_account": {},
                "jwt_token": None,
                "authenticated": False
            }

        return state

    def update_profile_from_response(
        self,
        api_response: Dict[str, Any],
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
            profile_data = self._structure_profile_data(api_response, action_type)

            # Get current state
            current_state = self._get_required_state()

            # Update token if provided
            if token:
                current_state["jwt_token"] = token

            # Handle account setup if dashboard data present
            dashboard_data = api_response.get("data", {}).get("dashboard")
            if dashboard_data:
                self._handle_account_setup(dashboard_data, current_state)

            # Update state with new profile
            self._update_state_with_profile(profile_data, current_state, update_from)

        except Exception as e:
            logger.error(f"Error updating profile from response: {str(e)}")
            raise

    def handle_successful_refresh(
        self,
        member_info: Dict[str, Any],
        current_state: Dict[str, Any]
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

            # Add current state's action data to member info to preserve it
            if "data" not in member_info:
                member_info["data"] = {}
            if "action" not in member_info["data"]:
                member_info["data"]["action"] = {}

            # Preserve existing action data while keeping any new action data
            current_action = current_state.get("profile", {}).get("action", {})
            existing_action = member_info["data"]["action"]
            member_info["data"]["action"].update({
                "id": existing_action.get("id", current_action.get("id", "")),
                "message": current_action.get("message", ""),  # Preserve message from current state
                "status": current_action.get("status", ""),  # Preserve status from current state
                "type": current_action.get("type", "refresh"),  # Preserve type from current state
                "details": existing_action.get("details", current_action.get("details", {}))  # Keep any new details
            })

            # Structure profile data
            profile_data = self._structure_profile_data(member_info, "refresh")
            profile_data["dashboard"] = dashboard_data

            # Validate current_state
            if not isinstance(current_state, dict):
                logger.warning("Invalid current_state format, initializing new state")
                current_state = {}

            # Update state with new profile data
            current_state["profile"] = profile_data

            # Handle account setup
            self._handle_account_setup(dashboard_data, current_state)

            # Update state
            channel_identifier = self.bot_service.user.state_manager.get("channel", {}).get("identifier")
            user = CachedUser(channel_identifier)
            user.state.update_state(current_state)

            logger.info("State updated successfully after refresh")
            return None

        except Exception as e:
            logger.error(f"Error handling refresh: {str(e)}")
            return str(e)
