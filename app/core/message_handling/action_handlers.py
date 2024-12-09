import logging
from ..utils.utils import wrap_text
from core.message_handling.whatsapp_forms import registration_form, offer_credex
from datetime import datetime, timedelta

from .screens import (
    UNSERCURED_BALANCES,
    CONFIRM_SECURED_CREDEX,
    CONFIRM_UNSECURED_CREDEX,
    BALANCE,
    HOME_1,
    HOME_2,
    OFFER_CREDEX,
    OFFER_SUCCESSFUL,
    ACCEPT_CREDEX,
    OUTGOING_CREDEX,
    CREDEX,
)
from ..config.constants import (
    INVALID_ACTION,
    CachedUser,
    CredexBotService,
)
from serializers.members import MemberDetailsSerializer
from serializers.offers import OfferCredexSerializer


class ActionHandler:
    """Handles various actions for the WhatsApp bot service."""

    def __init__(self, service: "CredexBotService"):
        """Initialize the action handler with a bot service.

        Args:
            service: The CredexBotService instance to use for handling actions
        """
        self.service = service

    def handle_action_register(self, register=False):
        """Handle user registration action.

        Args:
            register: Whether this is a new registration

        Returns:
            Response message or form
        """
        if register:
            return registration_form(
                self.service.user.mobile_number,
                "*Welcome To Credex!*\n\nIt looks like you're new here. "
                "Let's get you \nset up.",
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
                    return wrap_text(message, self.service.user.mobile_number)
            else:
                logging.error("Invalid registration data")

    def handle_action_menu(self, message=None, login=False):
        """Handle menu action and display appropriate menu options.

        Args:
            message: Optional message to display
            login: Whether this is a login action

        Returns:
            Menu response
        """
        user = CachedUser(self.service.user.mobile_number)
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
                logging.error(f"Error updating state: {e}")

        pending = ""
        pending_in = 0
        if selected_account["data"]["pendingInData"]["data"]:
            pending_in = len(selected_account["data"]["pendingInData"]["data"])
            pending = f"    Pending Offers ({pending_in})"

        pending_out = 0
        if selected_account["data"]["pendingOutData"]["data"]:
            pending_out = len(selected_account["data"]["pendingOutData"]["data"])

        balances = ""
        secured = ""

        balance_data = selected_account.get("data", {}).get("balanceData", {}).get("data", {})
        is_owned_account = selected_account["data"].get("isOwnedAccount")
        for bal in balance_data["securedNetBalancesByDenom"]:
            balances += f"- {bal}\n"
            secured += f" *{bal}* \n"

        unsecured_balance = (
            UNSERCURED_BALANCES.format(
                totalPayables=balance_data["unsecuredBalancesInDefaultDenom"][
                    "totalPayables"
                ],
                totalReceivables=balance_data["unsecuredBalancesInDefaultDenom"][
                    "totalReceivables"
                ],
                netPayRec=balance_data["unsecuredBalancesInDefaultDenom"]["netPayRec"],
            )
            if member_tier > 2
            else (
                f"Free tier remaining daily spend limit\n"
                f"    *{current_state['profile'].get('remainingAvailableUSD', '0.00')} "
                f"USD*\n{pending}\n"
            )
        )

        balance_text = BALANCE.format(
            securedNetBalancesByDenom=(balances if balances else "    $0.00\n"),
            unsecured_balance=unsecured_balance,
            netCredexAssetsInDefaultDenom=balance_data["netCredexAssetsInDefaultDenom"],
        )

        menu_text = (HOME_2 if is_owned_account else HOME_1).format(
            message=message if message else "",
            account=current_state.get("current_account", {}).get(
                "accountName", "Personal Account"
            ),
            balance=balance_text,
            handle=current_state["current_account"]["data"]["accountHandle"],
        )

        base_menu_rows = [
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

        extended_menu_rows = base_menu_rows + [
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
        ]

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.service.user.mobile_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": menu_text},
                "action": {
                    "button": "🕹️ Options",
                    "sections": [
                        {
                            "title": "Options",
                            "rows": (
                                extended_menu_rows
                                if is_owned_account and member_tier > 2
                                else base_menu_rows
                            ),
                        }
                    ],
                },
            },
        }

    def handle_action_select_profile(self, message=None):
        """Handle profile selection action."""
        pass

    def handle_action_pending_offers_in(self):
        """Handle displaying incoming offers."""
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        if not current_state.get("profile"):
            self.service.api_interactions.refresh_member_info()
            user = CachedUser(self.service.user.mobile_number)
            current_state = user.state.get_state(self.service.user)

        if user.state.option == "handle_action_display_offers":
            data = (
                current_state.get("current_account", {})
                .get("data", {})
                .get("pendingInData", {})
                .get("data", [])
            )
            if (
                self.service.body in [str(i) for i in range(1, len(data) + 1)]
                or self.service.message["type"] == "interactive"
            ):
                if data:
                    item = None
                    if self.service.body.isdigit():
                        item = data[int(self.service.body) - 1]
                    else:
                        for row in data:
                            if row.get("credexID") == self.service.body:
                                item = row
                                break

                    if item:
                        return {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": self.service.user.mobile_number,
                            "type": "interactive",
                            "interactive": {
                                "type": "button",
                                "body": {
                                    "text": ACCEPT_CREDEX.format(
                                        amount=item.get("formattedInitialAmount"),
                                        party=item.get("counterpartyAccountName"),
                                        type=(
                                            "Secured"
                                            if item.get("secured")
                                            else "Unsecured"
                                        ),
                                    )
                                },
                                "action": {
                                    "buttons": [
                                        {
                                            "type": "reply",
                                            "reply": {
                                                "id": f"decline_{item.get('credexID')}",
                                                "title": "❌ Decline",
                                            },
                                        },
                                        {
                                            "type": "reply",
                                            "reply": {
                                                "id": f"accept_{item.get('credexID')}",
                                                "title": "✅ Accept",
                                            },
                                        },
                                    ]
                                },
                            },
                        }

        if self.service.body == "handle_action_pending_offers_in":
            rows = []
            menu_string = "> *📥 Pending Incoming*\n"
            data = (
                current_state.get("current_account", {})
                .get("data", {})
                .get("pendingInData", {})
                .get("data", [])
            )
            for count, item in enumerate(data[:10], start=1):
                menu_string += (
                    f"\n{count}. *Total Credex Amount :* "
                    f"{item.get('formattedInitialAmount')}\n"
                    f"        *From :* {item.get('counterpartyAccountName')}\n"
                )
                rows.append(
                    {
                        "id": item.get("credexID"),
                        "title": item.get("formattedInitialAmount"),
                        "description": f"from {item.get('counterpartyAccountName')}",
                    }
                )

            user.state.update_state(
                state=current_state,
                stage="handle_action_pending_offers_in",
                update_from="handle_action_pending_offers_in",
                option="handle_action_display_offers",
            )

            if not rows:
                menu_string = "*Empty*\n\n🪹 No pending offers to display!\n\n"
                rows = [{"id": "X", "title": "🏡 Menu"}]
                return wrap_text(
                    user_mobile_number=self.service.user.mobile_number,
                    message=menu_string,
                    extra_rows=rows,
                )

            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": menu_string},
                    "action": {
                        "button": "✅ Accept All",
                        "sections": [
                            {
                                "title": "Options",
                                "rows": [
                                    {
                                        "id": "AcceptAllIncomingOffers",
                                        "title": "✅ Accept All",
                                    }
                                ],
                            }
                        ],
                    },
                },
            }
        else:
            if self.service.body == "AcceptAllIncomingOffers":
                return self.handle_action_accept_all_incoming_offers()

    def handle_action_accept_offer(self):
        """Handle accepting an offer."""
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        payload = {
            "credexID": self.service.body.split("_")[-1],
            "signerID": current_state["profile"]["member"].get("memberID"),
        }
        successful, message = self.service.api_interactions.accept_credex(payload)

        if successful:
            secured = ""
            for item in message["data"]["dashboard"]["data"]["balanceData"]["data"][
                "securedNetBalancesByDenom"
            ]:
                secured += f" *{item}* \n"

            balances = ""
            balance_lists = message["data"]["dashboard"]["data"]["balanceData"]["data"][
                "unsecuredBalancesInDefaultDenom"
            ]
            for bal in balance_lists.keys():
                balances += f"- {bal} {balance_lists[bal]}\n"

            balance_data = BALANCE.format(
                securedNetBalancesByDenom=secured if secured else "    $0.00\n",
                unsecured_balance=balances,
                netCredexAssetsInDefaultDenom=message["data"]["dashboard"]["data"][
                    "balanceData"
                ]["data"]["netCredexAssetsInDefaultDenom"],
            )

            return wrap_text(
                message=f"> 💸 *SUCCESS* \n\n{balance_data}\n"
                "*Successfully Accepted Credex*\n",
                user_mobile_number=self.service.user.mobile_number,
                extra_rows=[],
            )
        else:
            return wrap_text(
                message=message,
                user_mobile_number=self.service.user.mobile_number,
                extra_rows=[],
            )

    def handle_action_decline_offer(self):
        """Handle declining an offer."""
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        payload = {
            "credexID": self.service.body.split("_")[-1],
            "signerID": current_state["profile"]["member"].get("memberID"),
        }
        successful, _ = self.service.api_interactions.decline_credex(payload)
        if successful:
            return wrap_text(
                message="*Offer declined successfully*",
                user_mobile_number=self.service.user.mobile_number,
                extra_rows=[],
            )
        else:
            return wrap_text(
                message="*Failed to decline offer*",
                user_mobile_number=self.service.user.mobile_number,
                extra_rows=[],
            )

    def handle_action_cancel_offer(self):
        """Handle cancelling a single offer."""
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        if not isinstance(current_state, dict):
            current_state = current_state.state

        payload = {
            "credexID": self.service.body.split("_")[-1],
            "signerID": current_state["profile"]["member"].get("memberID"),
        }
        successful, _ = self.service.api_interactions.cancel_credex(payload)
        if successful:
            return wrap_text(
                message="> *Cancelled by issuer*\n\n"
                "*Credex has been cancelled successfully*",
                user_mobile_number=self.service.user.mobile_number,
                extra_rows=[],
            )
        else:
            return wrap_text(
                message="*Credex could not be cancelled*",
                user_mobile_number=self.service.user.mobile_number,
                extra_rows=[],
            )

    def handle_action_accept_all_incoming_offers(self):
        """Handle accepting all incoming offers."""
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        data = (
            current_state.get("current_account", {})
            .get("data", {})
            .get("pendingInData", {})
            .get("data", [])
        )
        payload = {
            "signerID": current_state["profile"]["member"].get("memberID"),
            "credexIDs": [i.get("credexID") for i in data],
        }
        status, message = self.service.api_interactions.accept_bulk_credex(payload)
        if status:
            secured = ""
            for item in message["dashboardData"]["balanceData"][
                "securedNetBalancesByDenom"
            ]:
                secured += f" *{item}* \n"

            balances = ""
            balance_lists = message["dashboardData"]["balanceData"][
                "securedNetBalancesByDenom"
            ]
            for bal in balance_lists:
                balances += f"- {bal}\n"

            message = BALANCE.format(
                securedNetBalancesByDenom=balances if balances else "    $0.00\n",
                unsecured_balance="",
                netCredexAssetsInDefaultDenom=message["dashboardData"]["balanceData"][
                    "netCredexAssetsInDefaultDenom"
                ],
            )

            user.state.update_state(
                state=current_state,
                stage="handle_action_menu",
                update_from="handle_action_accept_all_incoming_offers",
                option="handle_action_menu",
            )
            return wrap_text(
                message=f"> 💸 *SUCCESS* \n\n{message}\n"
                " *All offers accepted successfully*",
                user_mobile_number=self.service.user.mobile_number,
                x_is_menu=True,
            )
        else:
            return wrap_text(
                message="*Failed to accept all offers*",
                user_mobile_number=self.service.user.mobile_number,
                x_is_menu=True,
            )

    def handle_action_pending_offers_out(self):
        """Handle displaying outgoing offers."""
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        if user.state.option == "handle_action_display_offers":
            data = (
                current_state.get("current_account", {})
                .get("data", {})
                .get("pendingOutData", {})
                .get("data", [])
            )
            if (
                self.service.body in [str(i) for i in range(1, len(data) + 1)]
                or self.service.message["type"] == "interactive"
            ):
                if data:
                    item = None
                    if self.service.body.isdigit():
                        item = data[int(self.service.body) - 1]
                    else:
                        for row in data:
                            if row.get("credexID") == self.service.body:
                                item = row
                                break
                    return {
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": self.service.user.mobile_number,
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {
                                "text": OUTGOING_CREDEX.format(
                                    amount=item.get("formattedInitialAmount"),
                                    party=item.get("counterpartyAccountName"),
                                    type=(
                                        "Secured"
                                        if item.get("secured")
                                        else "Unsecured"
                                    ),
                                )
                            },
                            "action": {
                                "buttons": [
                                    {
                                        "type": "reply",
                                        "reply": {
                                            "id": f"cancel_{item.get('credexID')}",
                                            "title": "❌ Cancel",
                                        },
                                    }
                                ]
                            },
                        },
                    }

        if self.service.body == "handle_action_pending_offers_out":
            rows = []
            menu_string = "> *📤 Pending Outgoing*\n\n*Offers*\n"
            count = 1
            current_state.get("current_account", {}).get("pendingOutData")
            data = (
                current_state.get("current_account", {})
                .get("data", {})
                .get("pendingOutData", {})
                .get("data", [])
            )
            for item in data[:10]:
                counterparty = item.get("counterpartyAccountName")
                menu_string += (
                    f"{count}. *{item.get('formattedInitialAmount')}* "
                    f"outgoing offer sent to\n"
                    f"        {counterparty}\n"
                )
                rows.append(
                    {
                        "id": item.get("credexID"),
                        "title": item.get("formattedInitialAmount"),
                        "description": f"to {item.get('counterpartyAccountName')}",
                    }
                )
                count += 1

            user.state.update_state(
                state=current_state,
                stage="handle_action_pending_offers_out",
                update_from="handle_action_pending_offers_out",
                option="handle_action_display_offers",
            )

            if not rows:
                menu_string = "*Empty*\n\n🪹 No pending offers to display!\n\n"
                return wrap_text(
                    message=menu_string,
                    user_mobile_number=self.service.user.mobile_number,
                    x_is_menu=True,
                )

            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.service.user.mobile_number,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": menu_string},
                    "action": {
                        "button": "🕹️ Options",
                        "sections": [{"title": "Options", "rows": rows}],
                    },
                },
            }

    def handle_action_transactions(self):
        """Handle fetching and displaying transactions with pagination."""
        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        page_number = current_state.get("page_number", 0)

        if self.service.body in ["Next", "next", "handle_action_transactions"]:
            page_number += 1
        elif self.service.body in ["Prev", "prev"] and page_number > 1:
            page_number -= 1
        else:
            if self.service.body.isdigit():
                if (
                    0
                    < int(self.service.body)
                    <= len(current_state.get("current_page", []))
                ):
                    self.service.body = current_state["current_page"][
                        int(self.service.body) - 1
                    ]["id"]

            payload = {
                "credexID": self.service.body,
                "accountID": current_state["profile"]["member"].get("memberID"),
            }

            done, response = self.service.api_interactions.get_credex(payload)
            if done:
                credex = response
                if credex:
                    return {
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": self.service.user.mobile_number,
                        "type": "interactive",
                        "interactive": {
                            "type": "list",
                            "body": {
                                "text": CREDEX.format(
                                    formattedOutstandingAmount=credex["credexData"].get(
                                        "formattedOutstandingAmount"
                                    ),
                                    formattedInitialAmount=credex["credexData"].get(
                                        "formattedInitialAmount"
                                    ),
                                    counterpartyDisplayname=credex["credexData"].get(
                                        "counterpartyAccountName"
                                    ),
                                    date=(
                                        credex["credexData"].get("dateTime")
                                        if credex["credexData"].get("dateTime")
                                        else "N/A"
                                    ),
                                    type=credex["credexData"].get("transactionType"),
                                )
                            },
                            "action": {
                                "button": "🕹️ Menu",
                                "sections": [
                                    {
                                        "title": "Options",
                                        "rows": [{"id": "X", "title": "🏡 Menu"}],
                                    }
                                ],
                            },
                        },
                    }

            menu_string = "*Empty*\n\n🪹 No transaction(s) found!\n\n"
            return wrap_text(
                message=menu_string,
                user_mobile_number=self.service.user.mobile_number,
                x_is_menu=True,
            )

        payload = {
            "accountID": current_state["current_account"].get("accountID"),
            "numRows": 8,
            "startRow": (page_number * 7) - 7 if (page_number * 7) - 7 > 0 else 1,
        }

        done, transactions = self.service.api_interactions.get_ledger(payload)
        if done:
            has_next = True if len(transactions) > 7 else False
            rows = []
            menu_string = f"> *💳 TRANSACTIONS*\n\n*PAGE #{page_number}*\n\n"
            count = 1
            for txn in transactions:
                if "Next" in txn.get("formattedInitialAmount"):
                    continue

                nl = "\n"
                menu_string += (
                    f"*{count}.* *{txn.get('formattedInitialAmount')}* "
                    f"{'to ' if '-' in txn.get('formattedInitialAmount') else 'from '}"
                    f"{txn.get('counterpartyAccountName').replace('Personal', f'{nl}     Personal')}\n\n"
                )
                rows.append(
                    {
                        "id": txn.get("credexID"),
                        "title": (
                            f"{txn.get('formattedInitialAmount').replace('-', '')} "
                            f"{'DEBIT ' if '-' in txn.get('formattedInitialAmount') else 'CREDIT '}"
                        ),
                        "description": (
                            f"{txn.get('formattedInitialAmount')} "
                            f"{'to ' if '-' in txn.get('formattedInitialAmount') else 'from '}"
                            f"{txn.get('counterpartyAccountName')}"
                        ),
                    }
                )
                count += 1

            current_state["page_number"] = page_number
            current_state["current_page"] = rows
            user.state.update_state(
                state=current_state,
                stage="handle_action_transactions",
                update_from="handle_action_transactions",
                option="handle_action_transactions",
            )

            if page_number > 1:
                rows.append({"id": "Prev", "title": "< Prev", "description": "< Prev"})

            if has_next:
                rows.append({"id": "Next", "title": "Next >", "description": "Next >"})

            if rows:
                return {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": self.service.user.mobile_number,
                    "type": "interactive",
                    "interactive": {
                        "type": "list",
                        "body": {
                            "text": menu_string + "Send *'Menu'* to go back to Menu"
                        },
                        "action": {
                            "button": "🕹️ Options",
                            "sections": [{"title": "Options", "rows": rows}],
                        },
                    },
                }
            menu_string = "*Empty*\n\n🪹 No transactions found!\n\n"

            return wrap_text(
                message=menu_string,
                user_mobile_number=self.service.user.mobile_number,
                x_is_menu=True,
            )
        else:
            menu_string = "*Empty*\n\n🪹 No transactions found!\n\n"
            return wrap_text(
                message=menu_string,
                user_mobile_number=self.service.user.mobile_number,
                x_is_menu=True,
            )

    def handle_action_create_business_account(self):
        # Implementation for creating a business account
        pass

    def handle_action_authorize_member(self):
        # Implementation for authorizing a member
        pass

    def handle_action_offer_credex(self):
        """Handle credex offers."""

        user = CachedUser(self.service.user.mobile_number)
        current_state = user.state.get_state(self.service.user)

        # Get the selected profile
        selected_profile = current_state.get("current_account", {})

        # Get the member dashboard
        member_dashboard = current_state.get("memberDashboard", {})

        message = ""
        if not current_state.get("profile"):
            # Refresh the user state
            response = self.service.api_interactions.refresh_member_info()
            if response:
                self.service.state_manager.update_state(
                    new_state=self.service.current_state,
                    update_from="handle_action_offer_credex",
                    stage="handle_action_register",
                    option="handle_action_register",
                )
                return response

        member_tier = (
            current_state.get("member", {})
            .get("memberDashboard", {})
            .get("memberTier", {})
            .get("low", 1)
        )

        if not current_state.get("current_account", {}) and member_tier >= 2:
            # Select a default profile
            return self.handle_action_select_profile()
        else:
            if not selected_profile:
                selected_profile = current_state["profile"]["memberDashboard"][
                    "accounts"
                ][0]
                current_state["current_account"] = selected_profile
                self.service.state_manager.update_state(
                    new_state=current_state,
                    stage="handle_action_offer_credex",
                    update_from="handle_action_offer_credex",
                    option="handle_action_offer_credex",
                )

        payload = {}
        if (
            "=>" in f"{self.service.body}"
            or "->" f"{self.service.body}"
            or self.service.message["type"] == "nfm_reply"
        ):
            if self.service.message["type"] == "nfm_reply":
                payload = {
                    "authorizer_member_id": current_state["profile"]
                    .get("member", {})
                    .get("memberID"),
                    "issuer_member_id": selected_profile["data"]["accountID"],
                    "handle": self.service.body.get("handle"),
                    "amount": self.service.body.get("amount"),
                    "dueDate": (
                        self.service.body.get("due_date")
                        if self.service.body.get("due_date")
                        else (datetime.now() + timedelta(weeks=4)).timestamp() * 1000
                    ),
                    "currency": self.service.body.get("currency"),
                    "securedCredex": True,
                }

            if "=>" in f"{self.service.body}" or "->" f"{self.service.body}":
                if "=>" in f"{self.service.body}":
                    amount, user = f"{self.service.body}".split("=>")
                    if "=" in user:
                        user, _ = user.split("=")
                    from datetime import datetime

                    payload = {
                        "authorizer_member_id": current_state["profile"]["member"].get(
                            "memberID"
                        ),
                        "issuer_member_id": selected_profile["data"]["accountID"],
                        "handle": user,
                        "amount": amount,
                        "dueDate": (datetime.now()).timestamp() * 1000,
                        "currency": (
                            selected_profile["defaultDenom"]
                            if selected_profile
                            else current_state["profile"]
                            .get("member", {})
                            .get("defaultDenom")
                        ),
                        "securedCredex": True,
                    }

            if "->" in f"{self.service.body}":
                if "=" in f"{self.service.body}":
                    amount, user_date = f"{self.service.body}".split("->")
                    user, date = user_date.split("=")

                    try:
                        from datetime import datetime

                        # Try to parse the date string with the specified format
                        datetime.strptime(date, "%Y-%m-%d")

                    except ValueError:
                        # If a ValueError is raised, the date string is not in the correct format
                        return wrap_text(
                            OFFER_CREDEX.format(message="*Invalid Due Date❗*"),
                            user_mobile_number=self.service.user.mobile_number,
                            x_is_menu=True,
                        )
                else:
                    amount, user = f"{self.service.body}".split("->")
                    date = None

                from datetime import datetime, timedelta

                payload = {
                    "authorizer_member_id": current_state["profile"]
                    .get("member", {})
                    .get("memberID"),
                    "issuer_member_id": selected_profile["data"]["accountID"],
                    "handle": user,
                    "amount": amount,
                    "dueDate": (
                        datetime.strptime(date, "%Y-%m-%d").timestamp() * 1000
                        if date
                        else (datetime.now() + timedelta(weeks=4)).timestamp() * 1000
                    ),
                    "currency": (
                        selected_profile["data"]["defaultDenom"]
                        if selected_profile
                        else current_state["profile"]
                        .get("member", {})
                        .get("defaultDenom")
                    ),
                    "securedCredex": False,
                }

            serializer = OfferCredexSerializer(
                data=payload,
                context={"api_interactions": self.service.api_interactions},
            )
            if serializer.is_valid():
                accounts = []
                available_accounts = []
                count = 1
                account_string = ""
                print(
                    "PASSED VALIDATION : ",
                    current_state["profile"]["memberDashboard"]["accounts"],
                )
                for account in current_state["profile"]["memberDashboard"]["accounts"]:
                    print("ACCOUNT : ", account)
                    account = account.get("data", {})
                    if account.get("accountID") not in available_accounts:

                        account_string += (
                            f" *{count}.*  _{account.get('accountName')}_\n"
                        )
                        accounts.append(
                            {
                                "id": account.get("accountID"),
                                "title": f"👤{account.get('accountName')}",
                            }
                        )
                        available_accounts.append(account.get("accountID"))

                        if count > 8:
                            break
                        count += 1

                count += 1
                response = (
                    CONFIRM_SECURED_CREDEX.format(
                        party=serializer.validated_data.get("full_name"),
                        amount=serializer.validated_data.get("InitialAmount"),
                        currency=serializer.validated_data.get("Denomination"),
                        source=selected_profile.get("accountName"),
                        handle=serializer.validated_data.pop("handle"),
                        secured="*secured*",
                        accounts=account_string,
                    )
                    if serializer.validated_data.get("securedCredex")
                    else CONFIRM_UNSECURED_CREDEX.format(
                        party=serializer.validated_data.get("full_name"),
                        amount=serializer.validated_data.get("InitialAmount"),
                        currency=serializer.validated_data.get("Denomination"),
                        source=selected_profile.get("accountName"),
                        handle=serializer.validated_data.pop("handle"),
                        secured="*unsecured*",
                        date=f"*Due Date :* {serializer.validated_data.get('dueDate')}",
                        accounts=account_string,
                    )
                )

                print("RESPONSE : ", response)
                current_state["confirm_offer_payload"] = serializer.validated_data
                current_state["confirm_offer_payload"]["secured"] = (
                    serializer.validated_data["securedCredex"]
                )
                self.service.state_manager.update_state(
                    new_state=current_state,
                    stage="handle_action_offer_credex",
                    update_from="handle_action_offer_credex",
                    option="handle_action_confirm_offer_credex",
                )

                return {
                    "messaging_product": "whatsapp",
                    "to": self.service.user.mobile_number,
                    "recipient_type": "individual",
                    "type": "interactive",
                    "interactive": {
                        "type": "flow",
                        "body": {"text": response},
                        "action": {
                            "name": "flow",
                            "parameters": {
                                "flow_message_version": "3",
                                "flow_action": "navigate",
                                "flow_token": "not-used",
                                "flow_id": "382339094914403",
                                "flow_cta": "Sign & Send",
                                "flow_action_payload": {
                                    "screen": "OFFER_SECURED_CREDEX",
                                    "data": {"source_account": accounts},
                                },
                            },
                        },
                    },
                }
            else:
                print("ERROR : ", serializer.errors)
                for err in serializer.errors.keys():
                    if "This field is required." != serializer.errors[err][0]:
                        message = f"*{serializer.errors[err][0]}❗*"
                        break

        if user.state.option == "handle_action_confirm_offer_credex":
            to_credex = current_state.get("confirm_offer_payload")
            to_credex["issuerAccountID"] = selected_profile.get("accountID")
            if self.service.message["type"] == "nfm_reply":
                to_credex["issuerAccountID"] = self.service.message["message"][
                    "source_account"
                ]

            to_credex["memberID"] = member_dashboard.get("memberID")
            to_credex.pop("handle", None)
            if to_credex.get("securedCredex"):
                to_credex.pop("dueDate", None)
            to_credex.pop("secured", None)

            success, message = self.service.api_interactions.offer_credex(to_credex)
            # {
            #     'message': 'Secured credex for 0.02 USD offers created successfully',
            #     'data': {
            #         'action': {
            #             'id': 'fed8f896-c949-4604-b279-e243436ed711',
            #             'type': 'CREDEX_CREATED',
            #             'timestamp': '2024-11-21T09:41:49.791Z',
            #             'actor': '93af87ee-4f1d-4341-a224-826598407793',
            #             'details': {
            #                 'amount': '0.02',
            #                 'denomination': 'USD',
            #                 'securedCredex': True,
            #                 'receiverAccountID': '001ae1dc-6c4d-4e8f-b50a-bd3793727341',
            #                 'receiverAccountName': 'Garnet Sharara Personal'
            #             }
            #         },
            #         'dashboard': {
            #             'success': True,
            #             'data': {
            #                 'accountID': 'd3a68139-81de-4bdb-875a-494f747863fb',
            #                 'accountName': 'Takudzwa Sharara Personal',
            #                 'accountHandle': '263719624032',
            #                 'defaultDenom': 'USD',
            #                 'isOwnedAccount': True,
            #                 'authFor': [
            #                     {
            #                         'lastname': 'Sharara',
            #                         'firstname': 'Takudzwa',
            #                         'memberID': '93af87ee-4f1d-4341-a224-826598407793'
            #                     }
            #                 ],
            #                 'balanceData': {
            #                     'success': True,
            #                     'data': {
            #                         'securedNetBalancesByDenom': ['99.22 USD'],
            #                         'unsecuredBalancesInDefaultDenom': {
            #                             'totalPayables': '0.00 USD',
            #                             'totalReceivables': '0.00 USD',
            #                             'netPayRec': '0.00 USD'
            #                         },
            #                         'netCredexAssetsInDefaultDenom': '99.76 USD'
            #                     },
            #                     'message': 'Account balances retrieved successfully'
            #                 },
            #                 'pendingInData': {
            #                     'success': True, 'data': [],
            #                     'message': 'No pending offers found'
            #                 },
            #                 'pendingOutData': {
            #                     'success': True,
            #                     'data': [
            #                         {
            #                             'credexID': 'fed8f896-c949-4604-b279-e243436ed711',
            #                             'formattedInitialAmount': '-0.02 USD',
            #                             'counterpartyAccountName': 'Garnet Sharara Personal',
            #                             'secured': True
            #                         },
            #                         {
            #                             'credexID': '4c6b5039-0a95-44fe-81b0-ffd551984c59',
            #                             'formattedInitialAmount': '-0.02 USD',
            #                             'counterpartyAccountName': 'Garnet Sharara Personal',
            #                             'secured': True
            #                         },
            #                         {
            #                             'credexID': '80148a09-a2f3-490a-a7f6-b341307659ea',
            #                             'formattedInitialAmount': '-0.02 USD',
            #                             'counterpartyAccountName': 'Garnet Sharara Personal',
            #                             'secured': True
            #                         },
            #                         {
            #                             'credexID': '6b09726d-2f9b-4551-82f2-1a813e005be5',
            #                             'formattedInitialAmount': '-0.25 USD',
            #                             'counterpartyAccountName': 'Garnet Sharara Personal',
            #                             'secured': True
            #                         },
            #                         {
            #                             'credexID': '511288df-29ac-473b-9166-91dfb971071f',
            #                             'formattedInitialAmount': '-0.23 USD',
            #                             'counterpartyAccountName': 'Garnet Sharara Personal',
            #                             'secured': True
            #                         }
            #                     ],
            #                     'message': 'Retrieved 5 pending outgoing offers'
            #                 },
            #                 'sendOffersTo': {
            #                     'memberID': '93af87ee-4f1d-4341-a224-826598407793',
            #                     'firstname': 'Takudzwa',
            #                     'lastname': 'Sharara'
            #                 }
            #             },
            #             'message': 'Dashboard retrieved successfully'
            #         }
            #     }
            # }
            print(">>>>> ", message)
            if success:
                if message["data"].get("action", {}).get("type") == "CREDEX_CREATED":

                    response = message["data"].get("action", {}).get("details", {})
                    current_state.pop("confirm_offer_payload", {})
                    denomination = response.get("denomination", "USD")
                    current_state.pop("current_account", {})

                    success_message = OFFER_SUCCESSFUL.format(
                        type=(
                            "Secured Credex"
                            if response.get("securedCredex")
                            else "Unsecured Credex"
                        ),
                        amount=response.get("amount"),
                        currency=denomination,
                        recipient=response.get("receiverAccountName"),
                        source=selected_profile["data"]["accountName"],
                        secured=(
                            "*Secured* credex"
                            if response.get("securedCredex")
                            else "*Unsecured* credex"
                        ),
                    )

                    secured = ""
                    for item in message["data"]["dashboard"]["data"]["balanceData"][
                        "data"
                    ]["securedNetBalancesByDenom"]:
                        secured += f" *{item}* \n"

                    balances = ""
                    balance_lists = message["data"]["dashboard"]["data"]["balanceData"][
                        "data"
                    ]["unsecuredBalancesInDefaultDenom"]
                    for bal in balance_lists.keys():
                        balances += f"- {bal} {balance_lists[bal]}\n"

                    balance_data = BALANCE.format(
                        securedNetBalancesByDenom=secured if secured else "    $0.00\n",
                        unsecured_balance=balances,
                        netCredexAssetsInDefaultDenom=message["data"]["dashboard"][
                            "data"
                        ]["balanceData"]["data"]["netCredexAssetsInDefaultDenom"],
                    )

                    return wrap_text(
                        message=f"{success_message}{balance_data}",
                        user_mobile_number=self.service.user.mobile_number,
                        x_is_menu=True,
                    )
                else:
                    current_state.pop("confirm_offer_payload", {})
                    message = self.format_synopsis(
                        message.get("error", {}).replace("Error:", "")
                    )
            else:
                try:
                    current_state.pop("confirm_offer_payload", {})
                    message = self.format_synopsis(message.replace("Error:", ""))
                except Exception as e:
                    message = "Invalid option selected"
                    print("ERROR : ", e)

        self.service.state_manager.update_state(
            new_state=current_state,
            stage="handle_action_offer_credex",
            update_from="handle_action_offer_credex",
            option="handle_action_offer_credex",
        )
        return offer_credex(
            self.service.user.mobile_number, message=self.format_synopsis(message)
        )

    def handle_default_action(self):
        # Implementation for handling default or unknown actions
        return wrap_text(INVALID_ACTION, self.service.user.mobile_number)

    @staticmethod
    def format_synopsis(synopsis, style=None):
        formatted_synopsis = ""
        words = synopsis.split()
        line_length = 0

        for word in words:
            # If adding the word exceeds the line length, start a new line
            if line_length + len(word) + 1 > 35:
                formatted_synopsis += "\n"
                line_length = 0
            if style:
                word = f"{style}{word}{style}"
            formatted_synopsis += word + " "
            line_length += len(word) + 1

        return formatted_synopsis.strip()
