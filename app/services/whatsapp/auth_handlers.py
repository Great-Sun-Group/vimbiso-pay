"""Authentication and menu handlers"""
import logging
from typing import Any, Dict, Optional, Tuple

from .base_handler import BaseActionHandler
from .screens import ACCOUNT_HOME, BALANCE, REGISTER
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Redirect to member registration flow"""
        try:
            if register:
                # No need to set flow data here - will be set by _start_flow
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

            return self.handle_action_menu()

        except Exception as e:
            logger.error(f"Error in registration: {str(e)}")
            return self.get_response_template("Registration failed. Please try again.")

    def _attempt_login(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Attempt login and get dashboard data"""
        try:
            # Try login
            success, login_msg = self.service.credex_service._auth.login(
                self.service.user.mobile_number
            )
            if not success:
                if any(phrase in login_msg.lower() for phrase in ["new user", "new here", "member not found"]):
                    return False, "new user", None
                return False, login_msg, None

            # Store JWT token through user's state and propagate to all services
            jwt_token = self.service.credex_service._auth._jwt_token
            if jwt_token:
                self.service.user.state.update_state({
                    "jwt_token": jwt_token,
                    "authenticated": True
                }, "login_success")
                # Use property setter to properly propagate token
                self.service.credex_service.jwt_token = jwt_token

            # Get dashboard data
            success, data = self.service.credex_service._member.get_dashboard(
                self.service.user.mobile_number
            )
            if not success:
                return False, data.get("message", "Failed to load profile"), None

            return True, "Success", data

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False, str(e), None

    def handle_action_menu(self, message: Optional[str] = None, login: bool = False) -> WhatsAppMessage:
        """Display main menu"""
        try:
            current_state = self.service.user.state.state

            # Get fresh data if needed
            if login or not current_state.get("profile"):
                success, msg, data = self._attempt_login()
                if not success:
                    if any(phrase in msg.lower() for phrase in ["new user", "new here", "member not found"]):
                        return self.handle_action_register(register=True)
                    return self.get_response_template(msg)

                # Update profile data through user's state
                self.service.user.state.update_state({
                    "profile": data,
                    "flow_data": None  # Clear any active flow
                }, "profile_update")

            # Get selected account
            selected_account = self._get_selected_account()
            if isinstance(selected_account, WhatsAppMessage):
                return selected_account

            # Show menu
            return self._build_menu_response(selected_account, message)

        except Exception as e:
            logger.error(f"Menu error: {str(e)}")
            return self.get_response_template("Failed to load menu. Please try again.")

    def _get_selected_account(self) -> Any:
        """Get selected account"""
        try:
            current_state = self.service.user.state.state
            selected_account = current_state.get("current_account")

            if not selected_account:
                # Find personal account
                profile_data = current_state.get("profile", {})
                accounts = profile_data.get("data", {}).get("dashboard", {}).get("accounts", [])

                if not accounts:
                    return self.get_response_template("No accounts found")

                for account in accounts:
                    if (account.get("success") and
                            account["data"].get("accountHandle") == self.service.user.mobile_number):
                        # Store selected account through user's state
                        self.service.user.state.update_state({
                            "current_account": account
                        }, "account_select")
                        return account

                return self.get_response_template("Personal account not found")

            return selected_account

        except Exception as e:
            logger.error(f"Account error: {str(e)}")
            return self.get_response_template("Error loading account")

    def _build_menu_response(
        self,
        selected_account: Dict[str, Any],
        message: Optional[str] = None
    ) -> WhatsAppMessage:
        """Build menu display"""
        try:
            # Get counts
            pending_in = len(selected_account["data"]["pendingInData"].get("data", []))
            pending_out = len(selected_account["data"]["pendingOutData"].get("data", []))

            # Format balances
            balances = ""
            balance_data = selected_account["data"]["balanceData"]["data"]
            for bal in balance_data["securedNetBalancesByDenom"]:
                balances += f"  {bal}\n"

            # Get tier info
            profile_data = self.service.user.state.state.get("profile", {})
            details = profile_data.get("data", {}).get("action", {}).get("details", {})
            member_tier = details.get("memberTier", {}).get("low", 1)
            remaining_usd = details.get("remainingAvailableUSD") or "0.00"

            # Format tier display
            tier_limit_display = ""
            if member_tier <= 2:
                tier_type = "OPEN" if member_tier == 1 else "VERIFIED"
                tier_limit_display = f"\n*{tier_type} TIER DAILY LIMIT*\n  ${remaining_usd} USD"

            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": ACCOUNT_HOME.format(
                            account=selected_account["data"].get("accountName", "Personal Account"),
                            handle=selected_account["data"]["accountHandle"],
                            balance=BALANCE.format(
                                securedNetBalancesByDenom=balances.rstrip(),
                                netCredexAssetsInDefaultDenom=balance_data["netCredexAssetsInDefaultDenom"],
                                tier_limit_display=tier_limit_display
                            )
                        )
                    },
                    "action": self._get_menu_actions(
                        selected_account["data"].get("isOwnedAccount", False),
                        pending_in,
                        pending_out,
                        member_tier
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Menu build error: {str(e)}")
            return self.get_response_template("Failed to build menu")

    def _get_menu_actions(
        self,
        is_owned_account: bool,
        pending_in: int,
        pending_out: int,
        member_tier: int
    ) -> Dict[str, Any]:
        """Get menu options"""
        base_options = [
            {
                "id": "offer_credex",
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

        if member_tier <= 2:
            base_options.append({
                "id": "upgrade_tier",
                "title": "⭐️ Upgrade Member Tier",
            })

        return {
            "button": "🕹️ Options",
            "sections": [{"title": "Options", "rows": base_options}],
        }
