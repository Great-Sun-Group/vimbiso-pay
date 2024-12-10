from typing import Dict, Any, Optional, Tuple

from .base_handler import BaseActionHandler
from .forms import registration_form
from .screens import HOME_1, HOME_2, BALANCE, UNSECURED_BALANCES
from .types import WhatsAppMessage
from api.serializers.members import MemberDetailsSerializer
from services.state.service import StateStage
import logging

logger = logging.getLogger(__name__)


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Handle user registration flow with proper state management

        Args:
            register: Whether this is a new registration

        Returns:
            WhatsAppMessage: Registration form or menu response
        """
        try:
            if register:
                # Initialize state with required fields before starting registration
                self.service.state.update_state(
                    user_id=self.service.user.mobile_number,
                    new_state={
                        "registration_started": True,
                        "stage": StateStage.AUTH.value,
                        "option": "registration"
                    },
                    stage=StateStage.AUTH.value,
                    update_from="registration_start",
                    option="registration"
                )
                return registration_form(
                    self.service.user.mobile_number,
                    "*Welcome To Credex!*\n\nIt looks like you're new here. Let's get you \nset up.",
                )

            if self.service.message_type == "nfm_reply":
                payload = {
                    "first_name": self.service.body.get("firstName"),
                    "last_name": self.service.body.get("lastName"),
                    "phone_number": self.service.user.mobile_number,
                }
                serializer = MemberDetailsSerializer(data=payload)
                if serializer.is_valid():
                    successful, message = self.service.credex_service.register_member(
                        serializer.validated_data
                    )
                    if successful:
                        # Store JWT token in state after successful registration
                        current_state = self.service.current_state or {}
                        current_state["jwt_token"] = self.service.credex_service._jwt_token
                        current_state["stage"] = StateStage.MENU.value
                        current_state["option"] = "handle_action_menu"
                        # Update state after successful registration
                        self.service.state.update_state(
                            user_id=self.service.user.mobile_number,
                            new_state=current_state,
                            stage=StateStage.MENU.value,
                            update_from="registration_complete",
                            option="handle_action_menu"
                        )
                        return self.handle_action_menu(message=f"\n{message}\n\n")
                    else:
                        return self.get_response_template(message)

            return self.handle_default_action()
        except Exception as e:
            logger.error(f"Error in registration flow: {str(e)}")
            return self.get_response_template("Registration failed. Please try again.")

    def _attempt_login(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Attempt to login and get dashboard data

        Returns:
            Tuple[bool, str, Optional[Dict]]: Success flag, message, and dashboard data
        """
        try:
            # Try to login
            success, login_msg = self.service.credex_service._auth.login(
                self.service.user.mobile_number
            )
            if not success:
                # Check for both new user phrases and member not found message
                if any(phrase in login_msg.lower() for phrase in ["new user", "new here", "member not found"]):
                    return False, "new user", None
                return False, login_msg, None

            # Store JWT token after successful login
            jwt_token = self.service.credex_service._auth._jwt_token
            if jwt_token:
                current_state = self.service.current_state or {}
                current_state["jwt_token"] = jwt_token
                current_state["stage"] = StateStage.AUTH.value
                current_state["option"] = "handle_action_menu"
                self.service.state.update_state(
                    user_id=self.service.user.mobile_number,
                    new_state=current_state,
                    stage=StateStage.AUTH.value,
                    update_from="login",
                    option="handle_action_menu"
                )
                # Set token in credex service
                self.service.credex_service._jwt_token = jwt_token

            # Get dashboard data
            success, data = self.service.credex_service._member.get_dashboard(
                self.service.user.mobile_number
            )
            if not success:
                return False, data.get("message", "Failed to load profile"), None

            return True, "Success", data
        except Exception as e:
            logger.error(f"Login attempt failed: {str(e)}")
            return False, str(e), None

    def handle_action_menu(self, message: Optional[str] = None, login: bool = False) -> WhatsAppMessage:
        """Handle main menu display and navigation with proper state management

        Args:
            message: Optional message to display
            login: Whether to force login refresh

        Returns:
            WhatsAppMessage: Menu response
        """
        try:
            user = self.service.user
            current_state = self.service.current_state

            # Always get fresh data when login=True or no profile exists
            if login or not current_state.get("profile"):
                success, msg, data = self._attempt_login()
                if not success:
                    if any(phrase in msg.lower() for phrase in ["new user", "new here", "member not found"]):
                        return self.handle_action_register(register=True)
                    return self.get_response_template(msg)

                # Update state with fresh dashboard data
                current_state["profile"] = data
                current_state["last_refresh"] = True
                current_state["stage"] = StateStage.MENU.value
                current_state["option"] = "handle_action_menu"
                # Preserve JWT token
                if self.service.credex_service._jwt_token:
                    current_state["jwt_token"] = self.service.credex_service._jwt_token
                self.service.state.update_state(
                    user_id=user.mobile_number,
                    new_state=current_state,
                    stage=StateStage.MENU.value,
                    update_from="menu_refresh",
                    option="handle_action_menu"
                )

            # Get selected account
            selected_account = self._get_selected_account()
            if isinstance(selected_account, WhatsAppMessage):
                return selected_account

            # Build and return menu
            return self._build_menu_response(selected_account, message)

        except Exception as e:
            logger.error(f"Error handling menu action: {str(e)}")
            return self.get_response_template("Failed to load menu. Please try again.")

    def _get_selected_account(self) -> Any:
        """Get selected account with proper error handling

        Returns:
            Union[Dict, WhatsAppMessage]: Selected account or error message
        """
        try:
            current_state = self.service.current_state
            selected_account = current_state.get("current_account")

            if not selected_account:
                accounts = current_state["profile"]["data"]["dashboard"]["accounts"]
                if not accounts:
                    return self.get_response_template("No accounts found. Please try again later.")

                # Find personal account
                for account in accounts:
                    if (account.get("success") and
                            account["data"].get("accountHandle") == self.service.user.mobile_number):
                        selected_account = account
                        # Update state with selected account
                        current_state["current_account"] = selected_account
                        current_state["stage"] = StateStage.MENU.value
                        current_state["option"] = "handle_action_menu"
                        # Preserve JWT token
                        if self.service.credex_service._jwt_token:
                            current_state["jwt_token"] = self.service.credex_service._jwt_token
                        self.service.state.update_state(
                            user_id=self.service.user.mobile_number,
                            new_state=current_state,
                            stage=StateStage.MENU.value,
                            update_from="account_select",
                            option="handle_action_menu"
                        )
                        break
                else:
                    return self.get_response_template("Personal account not found. Please try again later.")

            return selected_account

        except (KeyError, IndexError) as e:
            logger.error(f"Error getting selected account: {str(e)}")
            return self.get_response_template("Error loading account information. Please try again.")

    def _build_menu_response(
        self,
        selected_account: Dict[str, Any],
        message: Optional[str] = None
    ) -> WhatsAppMessage:
        """Build menu response with proper error handling"""
        try:
            # Get pending offers counts for menu actions
            pending_in = len(selected_account["data"]["pendingInData"].get("data", []))
            pending_out = len(selected_account["data"]["pendingOutData"].get("data", []))

            # Format balances
            balances = ""
            balance_data = selected_account["data"]["balanceData"]["data"]
            is_owned_account = selected_account["data"].get("isOwnedAccount")

            for bal in balance_data["securedNetBalancesByDenom"]:
                balances += f"  {bal}\n"

            # Get member tier from dashboard data
            profile_data = self.service.current_state.get("profile", {})
            data = profile_data.get("data", {})
            action = data.get("action", {})
            details = action.get("details", {})
            member_tier = details.get("memberTier", {}).get("low", 1)

            # Get remaining available USD from either member or dashboard data
            remaining_usd = details.get("remainingAvailableUSD") or "0.00"

            # Determine what to show in the unsecured balance section
            if balance_data["unsecuredBalancesInDefaultDenom"]["totalPayables"] != "0.00 USD" or \
               balance_data["unsecuredBalancesInDefaultDenom"]["totalReceivables"] != "0.00 USD":
                # Show unsecured balances if they exist
                unsecured_balance = UNSECURED_BALANCES.format(
                    totalPayables=balance_data["unsecuredBalancesInDefaultDenom"]["totalPayables"],
                    totalReceivables=balance_data["unsecuredBalancesInDefaultDenom"]["totalReceivables"],
                    netPayRec=balance_data["unsecuredBalancesInDefaultDenom"]["netPayRec"],
                )
            elif member_tier <= 2:
                # Only show free tier limit for tier <= 2
                unsecured_balance = f"Free tier remaining daily spend limit\n    *{remaining_usd} USD*"
            else:
                # Show nothing for tier > 2
                unsecured_balance = ""

            # Build menu response
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": (HOME_2 if is_owned_account else HOME_1).format(
                            message=message.strip() if message else "",
                            account=selected_account["data"].get("accountName", "Personal Account"),
                            balance=BALANCE.format(
                                securedNetBalancesByDenom=balances.rstrip(),
                                unsecured_balance=unsecured_balance,
                                netCredexAssetsInDefaultDenom=balance_data[
                                    "netCredexAssetsInDefaultDenom"
                                ],
                            ),
                            handle=selected_account["data"]["accountHandle"],
                        )
                    },
                    "action": self._get_menu_actions(is_owned_account, pending_in, pending_out),
                },
            }
        except Exception as e:
            logger.error(f"Error building menu response: {str(e)}")
            return self.get_response_template("Failed to load menu. Please try again later.")

    def _get_menu_actions(
        self,
        is_owned_account: bool,
        pending_in: int,
        pending_out: int
    ) -> Dict[str, Any]:
        """Get menu actions based on account type"""
        base_options = [
            {
                "id": "handle_action_offer_credex",
                "title": "💸 Offer Secured Credex",
            },
            {
                "id": "handle_action_pending_offers_in",
                "title": f"📥 Pending Offers ({pending_in})",
            },
            {
                "id": "handle_action_pending_offers_out",
                "title": f"❌ Cancel Outgoing ({pending_out})",
            },
            {
                "id": "handle_action_transactions",
                "title": "📒 Review Transactions",
            },
        ]

        return {
            "button": "🕹️ Options",
            "sections": [{"title": "Options", "rows": base_options}],
        }

    def handle_action_select_profile(self) -> WhatsAppMessage:
        """Handle profile selection with proper state management"""
        try:
            # Update state for profile selection
            current_state = self.service.current_state or {}
            # Preserve JWT token
            if self.service.credex_service._jwt_token:
                current_state["jwt_token"] = self.service.credex_service._jwt_token
            current_state["selecting_profile"] = True
            current_state["stage"] = StateStage.ACCOUNT.value
            current_state["option"] = "profile_selection"
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.ACCOUNT.value,
                update_from="profile_select",
                option="profile_selection"
            )
            # Implementation for selecting a profile
            return self.get_response_template("Profile selection not implemented")
        except Exception as e:
            logger.error(f"Error in profile selection: {str(e)}")
            return self.get_response_template("Profile selection failed. Please try again.")
