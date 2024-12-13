"""Authentication and menu handlers"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .base_handler import BaseActionHandler
from .screens import HOME_1, HOME_2, BALANCE, REGISTER
from .types import WhatsAppMessage
from services.state.service import StateStage
from services.whatsapp.handlers.member.handler import MemberRegistrationHandler
import logging

logger = logging.getLogger(__name__)


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def __init__(self, service):
        super().__init__(service)
        self.registration_handler = MemberRegistrationHandler(service)

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Handle user registration flow with proper state management

        Args:
            register: Whether this is a new registration

        Returns:
            WhatsAppMessage: Registration response
        """
        try:
            if register:
                # Initialize state with required fields before starting registration
                self.service.state.update_state(
                    user_id=self.service.user.mobile_number,
                    new_state={
                        "registration_started": True,
                        "stage": StateStage.REGISTRATION.value,
                        "option": "registration"
                    },
                    stage=StateStage.REGISTRATION.value,
                    update_from="registration_start",
                    option="registration"
                )
                # Show welcome message with interactive button
                return {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": self.service.user.mobile_number,
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": REGISTER
                        },
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {
                                        "id": "start_registration",
                                        "title": "Introduce yourself"
                                    }
                                }
                            ]
                        }
                    }
                }

            # Handle registration through the registration handler
            return self.registration_handler.handle_registration()

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
                # Clear registration state if exists
                current_state.pop("registration_started", None)
                current_state.pop("flow_data", None)
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

            # Format tier limit display
            tier_limit_display = ""
            if member_tier <= 2:
                tier_type = "OPEN" if member_tier == 1 else "VERIFIED"
                tier_limit_display = f"\n*{tier_type} TIER DAILY LIMIT*\n  ${remaining_usd} USD"

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
                                netCredexAssetsInDefaultDenom=balance_data[
                                    "netCredexAssetsInDefaultDenom"
                                ],
                                tier_limit_display=tier_limit_display
                            ),
                            handle=selected_account["data"]["accountHandle"],
                        )
                    },
                    "action": self._get_menu_actions(is_owned_account, pending_in, pending_out, member_tier),
                },
            }
        except Exception as e:
            logger.error(f"Error building menu response: {str(e)}")
            return self.get_response_template("Failed to load menu. Please try again later.")

    def _get_menu_actions(
        self,
        is_owned_account: bool,
        pending_in: int,
        pending_out: int,
        member_tier: int
    ) -> Dict[str, Any]:
        """Get menu actions based on account type"""
        base_options = [
            {
                "id": "handle_action_offer_credex",
                "title": "💸 Offer Secured Credex",
            },
            {
                "id": "handle_action_accept_offers",
                "title": f"✅ Accept Offers ({pending_in})",
            },
            {
                "id": "handle_action_decline_offers",
                "title": f"❌ Decline Offers ({pending_in})",
            },
            {
                "id": "handle_action_pending_offers_out",
                "title": f"📤 Cancel Outgoing ({pending_out})",
            },
            {
                "id": "handle_action_transactions",
                "title": "📒 Review Transactions",
            },
        ]

        # Add upgrade option for eligible tiers
        if member_tier <= 2:
            base_options.append({
                "id": "handle_action_upgrade_tier",
                "title": "⭐️ Upgrade Member Tier",
            })

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

    def handle_action_upgrade_tier(self) -> WhatsAppMessage:
        """Handle member tier upgrade flow"""
        try:
            # Update state to track upgrade flow
            current_state = self.service.current_state
            current_state["stage"] = StateStage.MENU.value
            current_state["option"] = "handle_action_confirm_tier_upgrade"
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="upgrade_tier",
                option="handle_action_confirm_tier_upgrade"
            )

            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": (
                            "*Upgrade to the Hustler tier for $1/month.* "
                            "Subscribe with the button below to unlock unlimited credex transactions.\n\n"
                            "Clicking below authorizes a $1 payment to be automatically processed "
                            "from your credex account every 4 weeks (28 days), starting today."
                        )
                    },
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": "confirm_tier_upgrade",
                                    "title": "Hustle Hard"
                                }
                            }
                        ]
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error in tier upgrade: {str(e)}")
            return self.get_response_template("Tier upgrade failed. Please try again.")

    def handle_action_confirm_tier_upgrade(self) -> WhatsAppMessage:
        """Handle tier upgrade confirmation and payment processing"""
        try:
            # Get account ID from current state
            current_state = self.service.current_state
            selected_account = current_state.get("current_account")
            if not selected_account:
                return self.get_response_template("Account not found. Please try again.")

            account_id = selected_account["data"].get("accountID")
            if not account_id:
                return self.get_response_template("Account ID not found. Please try again.")

            # Create recurring payment request
            payment_data = {
                "sourceAccountID": account_id,
                "templateType": "MEMBERTIER_SUBSCRIPTION",
                "payFrequency": 28,
                "startDate": datetime.now().strftime("%Y-%m-%d"),
                "memberTier": 3,
                "securedCredex": True,
                "amount": 1.00,
                "denomination": "USD"
            }

            # Call createRecurring endpoint through recurring service
            success, response = self.service.credex_service._recurring.create_recurring(payment_data)
            if not success:
                error_msg = response.get("message", "Failed to process subscription")
                logger.error(f"Tier upgrade failed: {error_msg}")
                return self.get_response_template(f"Subscription failed: {error_msg}")

            # Update state before refreshing dashboard
            current_state["stage"] = StateStage.MENU.value
            current_state["option"] = "handle_action_menu"
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=StateStage.MENU.value,
                update_from="tier_upgrade_success",
                option="handle_action_menu"
            )

            # Return success message and refresh dashboard
            return self.handle_action_menu(
                message="🎉 Successfully upgraded to Hustler tier!",
                login=True
            )

        except Exception as e:
            logger.error(f"Error processing tier upgrade: {str(e)}")
            return self.get_response_template("Failed to process tier upgrade. Please try again.")
