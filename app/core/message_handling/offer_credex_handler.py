from ..utils.utils import wrap_text, format_synopsis, CredexWhatsappService
from ..config.constants import *
from serializers.offers import OfferCredexSerializer
import requests
import json
from decouple import config
from datetime import datetime, timedelta


class OfferCredexHandler:
    """Offering Credex Handler"""

    def __init__(self, service):
        self.service = service

    def handle_action_offer_credex(self):
        state = self.service.state
        current_state = self.service.current_state
        message = ""

        if not current_state.get("member"):
            self.service.refresh()

        if not current_state.get("member", {}).get("defaultAccountData", {}):
            for account in current_state["member"]["accountDashboards"]:
                if current_state["member"]["memberDashboard"]["accountIDS"][
                    -1
                ] == account.get("accountID"):
                    current_state["member"]["defaultAccountData"] = account
                    break

        payload = {}
        if (
            "=>" in f"{self.service.body}"
            or "->" in f"{self.service.body}"
            or self.service.message["type"] == "nfm_reply"
        ):
            payload = self._create_payload(current_state)

            serializer = OfferCredexSerializer(data=payload)
            if serializer.is_valid():
                return self._handle_valid_serializer(serializer, current_state, state)
            else:
                message = self._handle_invalid_serializer(serializer)

        if state.option == "handle_action_confirm_offer_credex":
            return self._handle_confirm_offer_credex(current_state, state)

        return self._create_offer_credex_response(current_state, state, message)

    def _create_payload(self, current_state):
        payload = {}
        if self.service.message["type"] == "nfm_reply":
            payload = self._create_nfm_reply_payload(current_state)
        elif "=>" in self.service.body:
            payload = self._create_secured_credex_payload(current_state)
        elif "->" in self.service.body:
            payload = self._create_unsecured_credex_payload(current_state)
        return payload

    def _create_nfm_reply_payload(self, current_state):
        return {
            "authorizer_member_id": current_state["member"]["memberDashboard"].get(
                "memberID"
            ),
            "issuer_member_id": (
                current_state["member"]["defaultAccountData"].get("accountID")
                if current_state.get("member", {}).get("defaultAccountData", {})
                else current_state["member"]["memberDashboard"]["accountIDS"][-1]
            ),
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

    def _create_secured_credex_payload(self, current_state):
        amount, user = f"{self.service.body}".split("=>")
        if "=" in user:
            user, _ = user.split("=")
        return {
            "authorizer_member_id": current_state["member"]["memberDashboard"].get(
                "memberID"
            ),
            "issuer_member_id": (
                current_state["member"]["defaultAccountData"].get("accountID")
                if current_state.get("member", {}).get("defaultAccountData", {})
                else current_state["member"]["memberDashboard"]["accountIDS"][-1]
            ),
            "handle": user,
            "amount": amount,
            "dueDate": (datetime.now()).timestamp() * 1000,
            "currency": (
                current_state["member"]["defaultAccountData"]["defaultDenom"]
                if current_state.get("member", {}).get("defaultAccountData", {})
                else current_state["member"]["memberDashboard"].get("defaultDenom")
            ),
            "securedCredex": True,
        }

    def _create_unsecured_credex_payload(self, current_state):
        if "=" in f"{self.service.body}":
            amount, user_date = f"{self.service.body}".split("->")
            user, date = user_date.split("=")
            try:
                due_date = datetime.strptime(date, "%Y-%m-%d").timestamp() * 1000
            except ValueError:
                raise ValueError("Invalid Due Date")
        else:
            amount, user = f"{self.service.body}".split("->")
            due_date = (datetime.now() + timedelta(weeks=4)).timestamp() * 1000

        return {
            "authorizer_member_id": current_state["member"]["memberDashboard"].get(
                "memberID"
            ),
            "issuer_member_id": (
                current_state["member"]["defaultAccountData"].get("accountID")
                if current_state.get("member", {}).get("defaultAccountData", {})
                else current_state["member"]["memberDashboard"]["accountIDS"][-1]
            ),
            "handle": user,
            "amount": amount,
            "dueDate": due_date,
            "currency": (
                current_state["member"]["defaultAccountData"]["defaultDenom"]
                if current_state.get("member", {}).get("defaultAccountData", {})
                else current_state["member"]["memberDashboard"].get("defaultDenom")
            ),
            "securedCredex": False,
        }

    def _handle_valid_serializer(self, serializer, current_state, state):
        accounts = self._get_accounts(current_state)
        response = self._create_confirmation_message(
            serializer, current_state, accounts
        )
        current_state["confirm_offer_payload"] = serializer.validated_data
        current_state["confirm_offer_payload"]["secured"] = serializer.validated_data[
            "securedCredex"
        ]
        state.update_state(
            state=current_state,
            stage="handle_action_offer_credex",
            update_from="handle_action_offer_credex",
            option="handle_action_confirm_offer_credex",
        )
        return self._create_confirmation_response(response, accounts)

    def _handle_invalid_serializer(self, serializer):
        for err in serializer.errors.keys():
            if "This field is required." != serializer.errors[err][0]:
                return f"*{serializer.errors[err][0]}❗*"
        return "Invalid input"

    def _handle_confirm_offer_credex(self, current_state, state):
        to_credex = current_state.get("confirm_offer_payload")
        to_credex["issuerAccountID"] = current_state["member"][
            "defaultAccountData"
        ].get("accountID")
        if self.service.message["type"] == "nfm_reply":
            to_credex["issuerAccountID"] = self.service.message["message"][
                "source_account"
            ]

        to_credex["memberID"] = current_state["member"]["memberDashboard"].get(
            "memberID"
        )
        to_credex.pop("handle", None)
        if to_credex.get("securedCredex"):
            to_credex.pop("dueDate", None)

        to_credex.pop("secured", None)
        payload = current_state.get("confirm_offer_payload")
        headers = {
            "X-Github-Token": config("CREDEX_API_CREDENTIALS"),
            "Content-Type": "application/json",
            "whatsappBotAPIkey": config("WHATSAPP_BOT_API_KEY"),
        }
        response = requests.request(
            "POST", f"{config('CREDEX')}/offerCredex", headers=headers, data=payload
        )

        if response.status_code == 200:
            return self._handle_successful_offer(response, current_state, state)
        else:
            return self._handle_failed_offer(response, current_state)

    def _create_offer_credex_response(self, current_state, state, message):
        from datetime import datetime, timedelta

        return {
            "messaging_product": "whatsapp",
            "to": self.service.user.mobile_number,
            "recipient_type": "individual",
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "body": {"text": OFFER_CREDEX.format(message=format_synopsis(message))},
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_action": "navigate",
                        "flow_token": "not-used",
                        "flow_id": "3435593326740751",
                        "flow_cta": " Offer Secured Credex",
                        "flow_action_payload": {
                            "screen": "MAKE_SECURE_OFFER",
                            "data": {
                                "min_date": str(
                                    (datetime.now() + timedelta(days=1)).timestamp()
                                    * 1000
                                ),
                                "max_date": str(
                                    (datetime.now() + timedelta(weeks=5)).timestamp()
                                    * 1000
                                ),
                            },
                        },
                    },
                },
            },
        }

    def _get_accounts(self, current_state):
        accounts = []
        for account in current_state["member"]["accountDashboards"]:
            accounts.append(
                {
                    "id": account.get("accountID"),
                    "title": f"👤 {account.get('accountName')}",
                }
            )
            if len(accounts) >= 8:
                break
        return accounts

    def _create_confirmation_message(self, serializer, current_state, accounts):
        account_string = "\n".join(
            [f" *{i + 1}.*  _{acc['title']}_" for i, acc in enumerate(accounts)]
        )
        if serializer.validated_data.get("securedCredex"):
            return CONFIRM_SECURED_CREDEX.format(
                party=serializer.validated_data.get("full_name"),
                amount=serializer.validated_data.get("InitialAmount"),
                currency=serializer.validated_data.get("Denomination"),
                source=current_state["member"]["defaultAccountData"].get("accountName"),
                handle=serializer.validated_data.pop("handle"),
                secured="*secured*",
                accounts=account_string,
            )
        else:
            return CONFIRM_UNSECURED_CREDEX.format(
                party=serializer.validated_data.get("full_name"),
                amount=serializer.validated_data.get("InitialAmount"),
                currency=serializer.validated_data.get("Denomination"),
                source=current_state["member"]["defaultAccountData"].get("accountName"),
                handle=serializer.validated_data.pop("handle"),
                secured="*unsecured*",
                date=f"*Due Date :* {serializer.validated_data.get('dueDate')}",
                accounts=account_string,
            )

    def _create_confirmation_response(self, response, accounts):
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

    def _handle_successful_offer(self, response, current_state, state):
        response_data = response.json()
        if response_data.get("offerCredexData", {}).get("credex"):
            credex_data = response_data.get("offerCredexData", {})
            current_state.pop("confirm_offer_payload", {})
            denom = current_state["member"]["defaultAccountData"]["defaultDenom"]
            current_state.pop("defaultAccountData", {})
            CredexWhatsappService(
                payload={
                    "messaging_product": "whatsapp",
                    "preview_url": False,
                    "recipient_type": "individual",
                    "to": self.service.user.mobile_number,
                    "type": "text",
                    "text": {
                        "body": OFFER_SUCCESSFUL.format(
                            type=(
                                "Secured Credex"
                                if credex_data["credex"]["secured"]
                                else "Unsecured Credex"
                            ),
                            amount=credex_data["credex"]["formattedInitialAmount"],
                            currency=denom,
                            recipient=credex_data["credex"]["counterpartyAccountName"],
                            source=current_state["member"]["defaultAccountData"].get(
                                "accountName"
                            ),
                            secured=(
                                "*Secured* credex"
                                if credex_data["credex"]["secured"]
                                else "*Unsecured* credex"
                            ),
                        )
                    },
                }
            ).notify()
            self._update_current_state(current_state)
            state.update_state(
                state=current_state,
                stage="handle_action_menu",
                update_from="handle_action_menu",
                option="handle_action_menu",
            )

            self.service.refresh(reset=True)
            self.service.body = current_state["member"]["defaultAccountData"].get(
                "accountHandle"
            )
            return self.service.action_handler.handle_action_select_profile()
        else:
            current_state.pop("confirm_offer_payload", {})
            message = format_synopsis(
                response_data.get("offerCredexData", {})
                .get("message", "")
                .replace("Error:", "")
            )
            return self._create_offer_credex_response(current_state, state, message)

    def _handle_failed_offer(self, response, current_state):
        current_state.pop("confirm_offer_payload", {})
        try:
            message = format_synopsis(
                response.json()
                .get("offerCredexData", {})
                .get("message", "")
                .replace("Error:", "")
            )
        except Exception:
            message = "Failed to process the offer"
        return wrap_text(
            OFFER_FAILED.format(message=message),
            self.service.user.mobile_number,
            x_is_menu=True,
            back_is_cancel=False,
        )

    def _update_current_state(self, current_state):
        default = current_state["member"]["defaultAccountData"].get("accountID")
        current_state.get("member", {}).pop("defaultAccountData", {})
        for account in current_state["member"]["accountDashboards"]:
            if default == account.get("accountID"):
                current_state["member"]["defaultAccountData"] = account
                break
