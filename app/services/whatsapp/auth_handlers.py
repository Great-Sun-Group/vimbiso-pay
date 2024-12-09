from typing import Dict, Any, Optional

from .base_handler import BaseActionHandler
from .forms import registration_form
from .screens import HOME_1, HOME_2, BALANCE, UNSERCURED_BALANCES
from .types import WhatsAppMessage
from api.serializers.members import MemberDetailsSerializer


class AuthActionHandler(BaseActionHandler):
    """Handler for authentication and menu-related actions"""

    def handle_action_register(self, register: bool = False) -> WhatsAppMessage:
        """Handle user registration flow

        Args:
            register: Whether this is a new registration

        Returns:
            WhatsAppMessage: Registration form or menu response
        """
        if register:
            return registration_form(
                self.service.user.mobile_number,
                "*Welcome To Credex!*\n\nIt looks like you're new here. Let's get you \nset up.",
            )

        if self.service.message["type"] == "nfm_reply":
            payload = {
                "first_name": self.service.body.get("firstName"),
                "last_name": self.service.body.get("lastName"),
                "phone_number": self.service.message["from"],
            }
            serializer = MemberDetailsSerializer(data=payload)
            if serializer.is_valid():
                successful, message = self.service.api_interactions.register_member(
                    serializer.validated_data
                )
                if successful:
                    self.service.state.update_state(
                        self.service.current_state,
                        stage="handle_action_menu",
                        update_from="handle_action_menu",
                        option="handle_action_menu",
                    )
                    return self.handle_action_menu(message=f"\n{message}\n\n")
                else:
                    return self.get_response_template(message)

        return self.handle_default_action()

    def handle_action_menu(self, message: Optional[str] = None, login: bool = False) -> WhatsAppMessage:
        """Handle main menu display and navigation

        Args:
            message: Optional message to display
            login: Whether this is after a login

        Returns:
            WhatsAppMessage: Menu response
        """
        user = self.service.user
        current_state = user.state.get_state(user)

        if not current_state.get("profile") or login:
            response = self.service.refresh(reset=True)
            current_state = user.state.get_state(user)
            if response and "error" in str(response).lower():
                self.service.state_manager.update_state(
                    new_state=self.service.current_state,
                    update_from="handle_action_menu",
                    stage="handle_action_register",
                    option="handle_action_register",
                )
                return response

        # Get member tier & selected account
        member_tier = (
            current_state.get("profile", {})
            .get("memberDashboard", {})
            .get("memberTier", {})
            .get("low", 1)
        )
        selected_account = current_state.get("current_account")

        if member_tier >= 2 and not selected_account:
            return self.handle_action_select_profile()

        if not selected_account:
            selected_account = current_state["profile"]["memberDashboard"]["accounts"][0]
            current_state["current_account"] = selected_account
            try:
                user.state.update_state(
                    state=current_state,
                    stage="handle_action_menu",
                    update_from="handle_action_menu",
                    option="handle_action_menu",
                )
                self.service.state_manager.update_state(
                    new_state=current_state,
                    stage="handle_action_menu",
                    update_from="handle_action_menu",
                    option="handle_action_menu",
                )
            except Exception as e:
                print("ERROR : ", e)

        # Get pending offers counts
        pending_in = len(selected_account["data"]["pendingInData"].get("data", []))
        pending_out = len(selected_account["data"]["pendingOutData"].get("data", []))
        pending = f"    Pending Offers ({pending_in})" if pending_in else ""

        # Format balances
        balances = ""
        secured = ""
        balance_data = selected_account["data"]["balanceData"]["data"]
        is_owned_account = selected_account["data"].get("isOwnedAccount")

        for bal in balance_data["securedNetBalancesByDenom"]:
            balances += f"- {bal}\n"
            secured += f" *{bal}* \n"

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
                        message=message if message else "",
                        account=current_state.get("current_account", {}).get(
                            "accountName", "Personal Account"
                        ),
                        balance=BALANCE.format(
                            securedNetBalancesByDenom=(
                                balances if balances else "    $0.00\n"
                            ),
                            unsecured_balance=(
                                UNSERCURED_BALANCES.format(
                                    totalPayables=balance_data[
                                        "unsecuredBalancesInDefaultDenom"
                                    ]["totalPayables"],
                                    totalReceivables=balance_data[
                                        "unsecuredBalancesInDefaultDenom"
                                    ]["totalReceivables"],
                                    netPayRec=balance_data[
                                        "unsecuredBalancesInDefaultDenom"
                                    ]["netPayRec"],
                                )
                                if member_tier > 2
                                else f"Free tier remaining daily spend limit\n    *{current_state['profile'].get('remainingAvailableUSD', '0.00')} USD*\n{pending}\n"
                            ),
                            netCredexAssetsInDefaultDenom=balance_data[
                                "netCredexAssetsInDefaultDenom"
                            ],
                        ),
                        handle=current_state["current_account"]["data"][
                            "accountHandle"
                        ],
                    )
                },
                "action": self._get_menu_actions(is_owned_account, member_tier, pending_in, pending_out),
            },
        }

    def _get_menu_actions(
        self,
        is_owned_account: bool,
        member_tier: int,
        pending_in: int,
        pending_out: int
    ) -> Dict[str, Any]:
        """Get menu actions based on account type and member tier

        Args:
            is_owned_account: Whether account is owned by user
            member_tier: User's member tier
            pending_in: Count of pending incoming offers
            pending_out: Count of pending outgoing offers

        Returns:
            Dict[str, Any]: Menu actions configuration
        """
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
                "title": f"📤 Review Outgoing ({pending_out})",
            },
            {
                "id": "handle_action_transactions",
                "title": "📒 Review Transactions",
            },
        ]

        if is_owned_account and member_tier > 2:
            base_options.extend([
                {
                    "id": "handle_action_authorize_member",
                    "title": "👥 Manage Members",
                },
                {
                    "id": "handle_action_notifications",
                    "title": "🛎️ Notifications",
                },
                {
                    "id": "handle_action_switch_account",
                    "title": "🏡 Member Dashboard",
                },
            ])

        return {
            "button": "🕹️ Options",
            "sections": [{"title": "Options", "rows": base_options}],
        }

    def handle_action_select_profile(self) -> WhatsAppMessage:
        """Handle profile selection"""
        # Implementation for selecting a profile
        return self.get_response_template("Profile selection not implemented")
