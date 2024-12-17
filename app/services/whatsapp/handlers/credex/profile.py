"""Profile mixin for credex handlers"""
import logging
from typing import Any, Dict, Tuple, Union

from services.state.service import StateStage
from ...types import WhatsAppMessage
from ...base_handler import BaseActionHandler

logger = logging.getLogger(__name__)


class ProfileMixin(BaseActionHandler):
    """Mixin for profile and account management functionality"""

    def _validate_and_get_profile(self) -> Union[Tuple[Dict[str, Any], Dict[str, Any]], WhatsAppMessage]:
        """Validate and get profile data with proper state management"""
        try:
            user = self.service.user
            current_state = self.service.current_state

            # Log current state for debugging
            logger.debug(f"Current state in validate_and_get_profile: {current_state}")

            # Always try to restore JWT token if present
            jwt_token = current_state.get("jwt_token")
            if jwt_token:
                logger.debug("Restoring JWT token from state")
                self.service.credex_service.jwt_token = jwt_token

            # Check if profile refresh needed
            profile_data = current_state.get("profile", {})
            needs_refresh = (
                not profile_data or
                not isinstance(profile_data, dict) or
                not profile_data.get("data", {}).get("dashboard", {}).get("accounts") or
                profile_data.get("data", {}).get("action", {}).get("details", {}) == {}  # Force refresh if empty details
            )

            if needs_refresh:
                logger.debug("Profile data missing or invalid, attempting refresh")
                if jwt_token:
                    # Only refresh if we have JWT token
                    logger.debug("Refreshing profile with JWT token")
                    response = self.service.refresh(reset=False)  # Don't reset state to preserve token
                    if response:
                        logger.error(f"Profile refresh failed: {response}")
                        return self.get_response_template("Error refreshing profile. Please try again by sending 'hi'.")
                    # Get fresh state after refresh
                    current_state = self.service.current_state
                    profile_data = current_state.get("profile", {})
                    logger.debug(f"Refreshed profile data: {profile_data}")
                else:
                    logger.error("JWT token missing, cannot refresh profile")
                    # Update state to trigger reauth
                    self.service.state.update_state(
                        user_id=user.mobile_number,
                        new_state={},
                        stage=StateStage.AUTH.value,
                        update_from="profile_refresh_auth",
                        option="handle_action_register"
                    )
                    return self.get_response_template("Please start over by sending 'hi' to refresh your session.")

            # Validate and structure profile data
            if not self._validate_profile_data(profile_data):
                logger.error("Invalid profile data structure")
                return self.get_response_template("Error validating profile. Please try again by sending 'hi'.")

            # Get selected profile
            selected_profile = current_state.get("current_account")
            if not selected_profile:
                logger.debug("No selected profile, finding personal account")
                selected_profile = self._find_personal_account(current_state)
                if isinstance(selected_profile, WhatsAppMessage):
                    return selected_profile

                # Update state with selected profile
                current_state["current_account"] = selected_profile
                # Always preserve JWT token
                if jwt_token:
                    current_state["jwt_token"] = jwt_token

                self.service.state.update_state(
                    user_id=user.mobile_number,
                    new_state=current_state,
                    stage=current_state.get("stage", StateStage.CREDEX.value),  # Preserve current stage
                    update_from="profile_select",
                    option=current_state.get("option", "handle_action_offer_credex")  # Preserve current option
                )
                logger.debug(f"Updated state with selected profile: {current_state}")

            return current_state, selected_profile

        except Exception as e:
            logger.error(f"Error in validate_and_get_profile: {str(e)}", exc_info=True)
            return self.get_response_template("Error validating profile. Please try again by sending 'hi'.")

    def _find_personal_account(self, current_state: Dict[str, Any]) -> Union[Dict[str, Any], WhatsAppMessage]:
        """Find personal account from available accounts"""
        try:
            # Get profile data with proper structure handling
            profile_data = current_state.get("profile", {})
            if not isinstance(profile_data, dict):
                logger.error("Profile data is not a dictionary")
                return self.get_response_template("Error loading account information. Please try again by sending 'hi'.")

            # Handle both direct and nested data structures
            data = profile_data.get("data", profile_data)
            if not isinstance(data, dict):
                logger.error("Profile data['data'] is not a dictionary")
                return self.get_response_template("Error loading account information. Please try again by sending 'hi'.")

            # Get dashboard data
            dashboard = data.get("dashboard", {})
            if not isinstance(dashboard, dict):
                logger.error("Dashboard data is not a dictionary")
                return self.get_response_template("Error loading account information. Please try again by sending 'hi'.")

            # Get accounts with proper validation
            accounts = dashboard.get("accounts", [])
            if not isinstance(accounts, list):
                logger.error("Accounts data is not a list")
                return self.get_response_template("Error loading account information. Please try again by sending 'hi'.")

            if not accounts:
                logger.error("No accounts found in profile data")
                return self.get_response_template("Account not found. Please try again by sending 'hi'.")

            # Look for personal account
            for account in accounts:
                if not isinstance(account, dict):
                    continue

                account_data = account.get("data", {})
                if (account.get("success") and
                    isinstance(account_data, dict) and
                        account_data.get("accountHandle") == self.service.user.mobile_number):
                    logger.debug(f"Found personal account: {account}")
                    return account

            # If no exact match, try to find first owned account
            for account in accounts:
                if not isinstance(account, dict):
                    continue

                account_data = account.get("data", {})
                if account.get("success") and account_data.get("isOwnedAccount"):
                    logger.debug(f"Found owned account: {account}")
                    return account

            logger.error("No suitable account found")
            return self.get_response_template("Account not found. Please try again by sending 'hi'.")

        except Exception as e:
            logger.error(f"Error finding personal account: {str(e)}", exc_info=True)
            return self.get_response_template("Error loading account information. Please try again by sending 'hi'.")

    def _validate_profile_data(self, profile_data: Dict[str, Any]) -> bool:
        """Validate profile data structure"""
        try:
            if not isinstance(profile_data, dict):
                logger.error("Profile data is not a dictionary")
                return False

            # Handle both direct and nested data structures
            data = profile_data.get("data", profile_data)
            if not isinstance(data, dict):
                logger.error("Profile data['data'] is not a dictionary")
                return False

            # Ensure profile structure exists
            if "action" not in data:
                data["action"] = {}
            if not isinstance(data["action"], dict):
                data["action"] = {}
            if "details" not in data["action"]:
                data["action"]["details"] = {}
            if not isinstance(data["action"]["details"], dict):
                data["action"]["details"] = {}

            # Update profile_data with structured data
            if "data" not in profile_data:
                profile_data["data"] = data
            else:
                profile_data["data"] = data

            # Check if data has dashboard info
            if "dashboard" in data:
                dashboard = data.get("dashboard", {})
                if not isinstance(dashboard, dict):
                    logger.error("Dashboard data is not a dictionary")
                    return False

                # Validate accounts structure
                accounts = dashboard.get("accounts", [])
                if not isinstance(accounts, list):
                    logger.error("Accounts data is not a list")
                    return False

                # Check at least one valid account
                valid_account = False
                for account in accounts:
                    if isinstance(account, dict) and account.get("success"):
                        valid_account = True
                        break

                if not valid_account:
                    logger.error("No valid accounts found")
                    return False

                # Check for memberID in details or try to get it from dashboard
                if "memberID" not in data["action"]["details"] and "memberID" in dashboard:
                    data["action"]["details"]["memberID"] = dashboard["memberID"]

            return True

        except Exception as e:
            logger.error(f"Profile validation error: {str(e)}", exc_info=True)
            return False
