from typing import Dict, Any, List

from core.transactions import (
    Transaction,
    TransactionOffer,
    TransactionType,
    TransactionError,
    create_transaction_service,
)
from .base_handler import BaseActionHandler
from .forms import offer_credex
from .screens import (
    CONFIRM_SECURED_CREDEX,
    CONFIRM_UNSECURED_CREDEX,
    OFFER_SUCCESSFUL,
)
from .types import WhatsAppMessage


class CredexActionHandler(BaseActionHandler):
    """Handler for Credex-related actions"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_service = create_transaction_service(
            api_client=self.service.api_interactions
        )

    def handle_action_offer_credex(self) -> WhatsAppMessage:
        """Handle credex offer creation"""
        user = self.service.user
        current_state = user.state.get_state(user)

        # Get the selected profile
        selected_profile = current_state.get("current_account", {})

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

        if not selected_profile:
            selected_profile = current_state["profile"]["memberDashboard"]["accounts"][0]
            current_state["current_account"] = selected_profile
            self.service.state_manager.update_state(
                new_state=current_state,
                stage="handle_action_offer_credex",
                update_from="handle_action_offer_credex",
                option="handle_action_offer_credex",
            )

        if self._is_credex_command(self.service.body):
            return self._handle_credex_command(current_state, selected_profile)

        if self.service.message["type"] == "nfm_reply":
            return self._handle_form_submission(current_state, selected_profile)

        if user.state.option == "handle_action_confirm_offer_credex":
            return self._handle_offer_confirmation(current_state, selected_profile)

        return offer_credex(self.service.user.mobile_number, message="")

    def _is_credex_command(self, body: str) -> bool:
        """Check if message is a credex command"""
        return "=>" in str(body) or "->" in str(body)

    def _handle_credex_command(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle credex command processing"""
        try:
            result = self.transaction_service.process_command(
                command=self.service.body,
                member_id=current_state["profile"]["member"].get("memberID"),
                account_id=selected_profile["data"]["accountID"],
                denomination=selected_profile["data"]["defaultDenom"],
            )

            if not result.success:
                return self._format_error_response(result.error_message)

            return self._format_confirmation_message(
                result.transaction.offer,
                current_state,
                self.transaction_service.get_available_accounts(
                    current_state["profile"]["member"].get("memberID")
                )
            )
        except TransactionError as e:
            return self._format_error_response(str(e))

    def _handle_form_submission(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle form submission processing"""
        try:
            offer = TransactionOffer(
                authorizer_member_id=current_state["profile"]["member"].get("memberID"),
                issuer_member_id=selected_profile["data"]["accountID"],
                amount=float(self.service.body.get("amount")),
                currency=self.service.body.get("currency"),
                type=TransactionType.SECURED_CREDEX,
                handle=self.service.body.get("handle"),
            )

            result = self.transaction_service.create_offer(offer)
            if not result.success:
                return self._format_error_response(result.error_message)

            return self._format_confirmation_message(
                result.transaction.offer,
                current_state,
                self.transaction_service.get_available_accounts(
                    current_state["profile"]["member"].get("memberID")
                )
            )
        except TransactionError as e:
            return self._format_error_response(str(e))

    def _handle_offer_confirmation(
        self, current_state: Dict[str, Any], selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Handle offer confirmation"""
        try:
            transaction_id = current_state.get("confirm_offer_payload", {}).get("id")
            if not transaction_id:
                return self._format_error_response("No transaction to confirm")

            issuer_account_id = (
                self.service.message["message"]["source_account"]
                if self.service.message["type"] == "nfm_reply"
                else selected_profile.get("accountID")
            )

            result = self.transaction_service.confirm_offer(
                transaction_id=transaction_id,
                issuer_account_id=issuer_account_id
            )

            if not result.success:
                return self._format_error_response(result.error_message)

            return self._format_success_response(result.transaction, selected_profile)
        except TransactionError as e:
            return self._format_error_response(str(e))

    def _format_confirmation_message(
        self,
        offer: TransactionOffer,
        current_state: Dict[str, Any],
        accounts: List[Dict[str, str]],
    ) -> WhatsAppMessage:
        """Format confirmation message for credex offer"""
        template = (
            CONFIRM_SECURED_CREDEX if offer.type == TransactionType.SECURED_CREDEX
            else CONFIRM_UNSECURED_CREDEX
        )

        date_str = (
            f"*Due Date :* {offer.due_date}"
            if offer.type == TransactionType.UNSECURED_CREDEX else ""
        )

        return {
            "messaging_product": "whatsapp",
            "to": self.service.user.mobile_number,
            "recipient_type": "individual",
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "body": {
                    "text": template.format(
                        party=offer.metadata.get("full_name"),
                        amount=offer.amount,
                        currency=offer.currency,
                        source=current_state.get("current_account", {}).get("accountName"),
                        handle=offer.handle,
                        secured="*secured*" if offer.type == TransactionType.SECURED_CREDEX else "*unsecured*",
                        date=date_str,
                    )
                },
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

    def _format_success_response(
        self, transaction: Transaction, selected_profile: Dict[str, Any]
    ) -> WhatsAppMessage:
        """Format success response for credex offer"""
        return self.get_response_template(
            OFFER_SUCCESSFUL.format(
                type="Secured Credex" if transaction.offer.type == TransactionType.SECURED_CREDEX
                else "Unsecured Credex",
                amount=transaction.offer.amount,
                currency=transaction.offer.currency,
                recipient=transaction.metadata.get("receiverAccountName"),
                source=selected_profile["data"]["accountName"],
                secured="*Secured* credex" if transaction.offer.type == TransactionType.SECURED_CREDEX
                else "*Unsecured* credex",
            )
        )

    def _format_error_response(self, message: str) -> WhatsAppMessage:
        """Format error response"""
        try:
            error_message = self.format_synopsis(
                message.replace("Error:", "")
            )
        except Exception:
            error_message = "Invalid option selected"

        return self.get_response_template(error_message)
