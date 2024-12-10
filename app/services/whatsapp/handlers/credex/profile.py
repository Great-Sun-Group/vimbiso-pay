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

            # Check if profile refresh needed
            if not current_state.get("profile"):
                response = self.service.refresh(reset=True)
                if response:
                    self.service.state.update_state(
                        user_id=user.mobile_number,
                        new_state={},
                        stage=StateStage.AUTH.value,
                        update_from="profile_refresh",
                        option="handle_action_register"
                    )
                    return self.get_response_template("Please log in again to continue.")

            # Get selected profile
            selected_profile = current_state.get("current_account")
            if not selected_profile:
                selected_profile = self._find_personal_account(current_state)
                if isinstance(selected_profile, WhatsAppMessage):
                    return selected_profile

                # Update state with selected profile
                current_state["current_account"] = selected_profile
                # Preserve JWT token
                if self.service.credex_service.jwt_token:
                    current_state["jwt_token"] = self.service.credex_service.jwt_token
                self.service.state.update_state(
                    user_id=user.mobile_number,
                    new_state=current_state,
                    stage="handle_action_offer_credex",
                    update_from="profile_select",
                    option="handle_action_offer_credex"
                )

            return current_state, selected_profile

        except Exception as e:
            logger.error(f"Error in validate_and_get_profile: {str(e)}")
            return self.get_response_template("Error validating profile. Please try again.")

    def _find_personal_account(self, current_state: Dict[str, Any]) -> Union[Dict[str, Any], WhatsAppMessage]:
        """Find personal account from available accounts"""
        try:
            accounts = current_state["profile"]["data"]["dashboard"]["accounts"]
            if not accounts:
                return self.get_response_template("No accounts found. Please try again later.")

            for account in accounts:
                if (account.get("success") and
                        account["data"].get("accountHandle") == self.service.user.mobile_number):
                    return account

            return self.get_response_template("Personal account not found. Please try again later.")
        except (KeyError, IndexError) as e:
            logger.error(f"Error finding personal account: {str(e)}")
            return self.get_response_template("Error loading account information. Please try again.")
