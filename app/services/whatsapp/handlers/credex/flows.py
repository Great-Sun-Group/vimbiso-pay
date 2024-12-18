"""Unified credex flow implementation"""
import logging
from typing import Any, Dict, List, Union
import re
from core.messaging.flow import Flow, Step, StepType
from core.transactions import TransactionOffer, TransactionType
from ...handlers.member.dashboard import DashboardFlow

logger = logging.getLogger(__name__)


class CredexFlow(Flow):
    """Base class for all credex flows"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:\(?([A-Z]{3})\)?)|(\d+(?:\.\d+)?))$')
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

    def __init__(self, flow_type: str, **kwargs):
        """Initialize flow"""
        self.flow_type = flow_type
        self.kwargs = kwargs
        steps = self._create_steps()
        super().__init__(f"credex_{flow_type}", steps)
        self.credex_service = None

    def _create_steps(self) -> List[Step]:
        """Create flow steps based on type"""
        if self.flow_type == "offer":
            return [
                Step(
                    id="amount",
                    type=StepType.TEXT,
                    message=self._get_amount_prompt,
                    validator=self._validate_amount,
                    transformer=self._transform_amount
                ),
                Step(
                    id="handle",
                    type=StepType.TEXT,
                    message=lambda s: self._create_whatsapp_message("Enter recipient handle:"),
                    validator=self._validate_handle,
                    transformer=self._transform_handle
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]
        elif self.flow_type == "cancel_credex":
            return [
                Step(
                    id="list",
                    type=StepType.LIST,
                    message=self._create_list_message,
                    validator=lambda x: x.startswith("cancel_"),
                    transformer=self._transform_cancel_selection
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]
        else:
            return [
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_confirmation_message,
                    validator=self._validate_button_response
                )
            ]

    def _create_whatsapp_message(self, text: str, message_type: str = "text", **kwargs) -> Dict[str, Any]:
        """Create standardized WhatsApp message"""
        message = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.data.get("mobile_number"),
            "type": message_type,
        }

        if message_type == "text":
            message["text"] = {"body": text}
        elif message_type == "interactive":
            message["interactive"] = kwargs.get("interactive", {})

        return message

    def _get_amount_prompt(self, _) -> Dict[str, Any]:
        """Get amount prompt message"""
        return self._create_whatsapp_message(
            "Enter amount:\n\n"
            "Examples:\n"
            "100     (USD)\n"
            "USD 100\n"
            "ZWG 100\n"
            "XAU 1"
        )

    def _create_list_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create list selection message"""
        pending_offers = state.get("pending_offers", [])
        rows = [
            {
                "id": f"cancel_{offer['id']}",
                "title": f"{offer['amount']} to {offer['to']}"
            }
            for offer in pending_offers
        ]

        return self._create_whatsapp_message(
            "Cancel Pending Outgoing Offers",
            "interactive",
            interactive={
                "type": "list",
                "body": {"text": "Select an offer to cancel:"},
                "action": {
                    "button": "🕹️ Options",
                    "sections": [{"title": "Pending Offers", "rows": rows}]
                }
            }
        )

    def _create_confirmation_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create confirmation message based on flow type"""
        messages = {
            "offer": self._create_offer_confirmation,
            "cancel_credex": self._create_cancel_confirmation,
            "accept": lambda s: self._create_action_confirmation(s, "Accept"),
            "decline": lambda s: self._create_action_confirmation(s, "Decline")
        }

        return messages[self.flow_type](state)

    def _create_offer_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create offer confirmation message"""
        amount = self._format_amount(
            state["amount"]["amount"],
            state["amount"]["denomination"]
        )
        handle = state["handle"]["handle"]
        name = state["handle"]["name"]

        return self._create_whatsapp_message(
            f"Confirm transaction:\n\n"
            f"Amount: {amount}\n"
            f"To: {name} ({handle})",
            "interactive",
            interactive={
                "type": "button",
                "body": {"text": f"Amount: {amount}\nTo: {name} ({handle})"},
                "action": {
                    "buttons": [{
                        "type": "reply",
                        "reply": {"id": "confirm_action", "title": "Confirm"}
                    }]
                }
            }
        )

    def _create_cancel_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create cancel confirmation message"""
        amount = state.get("amount", "0")
        counterparty = state.get("counterparty", "Unknown")

        return self._create_whatsapp_message(
            f"Cancel Credex Offer\n\n"
            f"Amount: {amount}\n"
            f"To: {counterparty}",
            "interactive",
            interactive={
                "type": "button",
                "body": {"text": f"Amount: {amount}\nTo: {counterparty}"},
                "action": {
                    "buttons": [{
                        "type": "reply",
                        "reply": {"id": "confirm_action", "title": "Cancel Offer"}
                    }]
                }
            }
        )

    def _create_action_confirmation(self, state: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Create action confirmation message"""
        amount = self._format_amount(
            float(state.get("amount", "0.00")),
            state.get("denomination", "USD")
        )
        counterparty = state.get("counterparty", "Unknown")

        return self._create_whatsapp_message(
            f"{action} credex offer\n\n"
            f"Amount: {amount}\n"
            f"From: {counterparty}",
            "interactive",
            interactive={
                "type": "button",
                "body": {"text": f"Amount: {amount}\nFrom: {counterparty}"},
                "action": {
                    "buttons": [{
                        "type": "reply",
                        "reply": {"id": "confirm_action", "title": "Confirm"}
                    }]
                }
            }
        )

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response"""
        return (
            response.get("type") == "interactive" and
            response.get("interactive", {}).get("type") == "button_reply" and
            response.get("interactive", {}).get("button_reply", {}).get("id") == "confirm_action"
        )

    def _transform_cancel_selection(self, selection: str) -> Dict[str, Any]:
        """Transform cancel selection"""
        credex_id = selection[7:] if selection.startswith("cancel_") else None
        if not credex_id:
            return {"error": "Invalid selection"}

        pending_offers = self.data.get("pending_offers", [])
        selected_offer = next(
            (offer for offer in pending_offers if offer["id"] == credex_id),
            None
        )

        if not selected_offer:
            return {"error": "Selected offer not found"}

        return {
            "credex_id": credex_id,
            "amount": selected_offer["amount"],
            "counterparty": selected_offer["to"]
        }

    def _validate_amount(self, amount_data: Union[str, Dict[str, Any]]) -> bool:
        """Validate amount format"""
        # Handle already transformed amount
        if isinstance(amount_data, dict):
            return (
                "amount" in amount_data and
                "denomination" in amount_data and
                isinstance(amount_data["amount"], (int, float)) and
                (not amount_data["denomination"] or amount_data["denomination"] in self.VALID_DENOMINATIONS)
            )

        # Handle string input
        if not amount_data:
            return False
        match = self.AMOUNT_PATTERN.match(str(amount_data).strip().upper())
        if not match:
            return False
        denom = match.group(1) or match.group(4)
        return not denom or denom in self.VALID_DENOMINATIONS

    def _transform_amount(self, amount_str: str) -> Dict[str, Any]:
        """Transform amount string to structured data"""
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())
        if match.group(1):  # Currency first
            denom, amount = match.group(1), match.group(2)
        elif match.group(3):  # Amount first
            amount, denom = match.group(3), match.group(4)
        else:  # Just amount
            amount, denom = match.group(5), None
        return {
            "amount": float(amount),
            "denomination": denom or "USD"
        }

    def _validate_handle(self, handle: str) -> bool:
        """Validate handle format"""
        return bool(handle and self.HANDLE_PATTERN.match(handle.strip()))

    def _transform_handle(self, handle: str) -> Dict[str, Any]:
        """Transform and validate handle"""
        if not self.credex_service:
            return {"error": "Service not initialized"}

        handle = handle.strip()
        success, response = self.credex_service._member.validate_handle(handle)
        if not success:
            return {"error": response.get("message", "Invalid handle")}

        data = response.get("data", {})
        return {
            "handle": handle,
            "account_id": data.get("accountID"),
            "name": data.get("accountName", handle)
        }

    def _format_amount(self, amount: float, denomination: str) -> str:
        """Format amount based on denomination"""
        if denomination in {"USD", "ZWG", "CAD"}:
            return f"${amount:.2f} {denomination}"
        elif denomination == "XAU":
            return f"{amount:.4f} {denomination}"
        return f"{amount} {denomination}"

    def _update_dashboard(self, response: Dict[str, Any]) -> None:
        """Update dashboard state"""
        try:
            if not hasattr(self.credex_service, '_parent_service'):
                return

            dashboard = response.get("data", {}).get("dashboard")
            if not dashboard:
                return

            user_state = self.credex_service._parent_service.user.state
            current_state = user_state.state
            current_profile = current_state.get("profile", {}).copy()

            # Preserve existing profile data
            if "data" in current_profile:
                current_profile["data"]["dashboard"] = dashboard
            else:
                current_profile["data"] = {"dashboard": dashboard}

            # Update state while preserving other critical fields
            user_state.update_state({
                "profile": current_profile,
                "current_account": current_state.get("current_account"),
                "jwt_token": current_state.get("jwt_token")
            }, "dashboard_update")

        except Exception as e:
            logger.error(f"Dashboard update error: {str(e)}")

    def complete(self) -> Union[str, Dict[str, Any]]:
        """Complete the flow"""
        try:
            if not self.credex_service:
                return "Service not initialized"

            handlers = {
                "offer": self._complete_offer,
                "cancel_credex": self._complete_cancel,
                "accept": lambda: self._complete_action("accept"),
                "decline": lambda: self._complete_action("decline")
            }

            return handlers[self.flow_type]()

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            return str(e)

    def _complete_cancel(self) -> Union[str, Dict[str, Any]]:
        """Complete cancel flow"""
        if self.current_step.id != "confirm":
            return self._create_list_message(self.data)

        credex_id = self.data.get("credex_id")
        if not credex_id:
            return "Missing credex ID"

        success, response = self.credex_service.cancel_credex(credex_id)
        if not success:
            return response.get("message", "Failed to cancel offer")

        self._update_dashboard(response)
        return self._show_dashboard("Credex successfully cancelled")

    def _complete_offer(self) -> Union[str, Dict[str, Any]]:
        """Complete offer flow"""
        offer = TransactionOffer(
            authorizer_member_id=self.data["member_id"],
            issuer_member_id=self.data["member_id"],
            receiver_account_id=self.data["handle"]["account_id"],
            amount=self.data["amount"]["amount"],
            denomination=self.data["amount"]["denomination"],
            type=TransactionType.SECURED_CREDEX,
            handle=self.data["handle"]["handle"],
            metadata={"name": self.data["handle"]["name"]}
        )

        success, response = self.credex_service.offer_credex({
            "authorizer_member_id": offer.authorizer_member_id,
            "issuerAccountID": self.data["account_id"],
            "receiverAccountID": offer.receiver_account_id,
            "InitialAmount": offer.amount,
            "Denomination": offer.denomination,
            "type": offer.type.value,
            "handle": offer.handle,
            "metadata": offer.metadata
        })

        if not success:
            return response.get("message", "Offer failed")

        self._update_dashboard(response)
        return self._show_dashboard("Credex successfully offered")

    def _complete_action(self, action: str) -> Union[str, Dict[str, Any]]:
        """Complete action flow"""
        credex_id = self.kwargs.get("credex_id")
        if not credex_id:
            return "Missing credex ID"

        actions = {
            "accept": self.credex_service.accept_credex,
            "decline": self.credex_service.decline_credex
        }

        success, response = actions[action](credex_id)
        if not success:
            return response.get("message", f"Failed to {action} offer")

        self._update_dashboard(response)
        return self._show_dashboard(f"Successfully {action}ed credex offer")

    def _show_dashboard(self, message: str) -> Dict[str, Any]:
        """Show dashboard with success message"""
        dashboard = DashboardFlow(success_message=message)
        dashboard.credex_service = self.credex_service
        dashboard.data = {"mobile_number": self.data.get("mobile_number")}
        return dashboard.complete()
