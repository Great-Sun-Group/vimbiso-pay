"""Unified credex flow implementation"""
import logging
import re
from typing import Any, Dict, List, Union

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
        """Initialize flow

        Args:
            flow_type: Type of flow ('offer', 'accept', 'decline', 'cancel_credex')
            **kwargs: Flow-specific arguments
        """
        logger.info(f"Initializing CredexFlow with type: {flow_type}")
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
                    message=lambda _: (
                        "Enter amount:\n\n"
                        "Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1"
                    ),
                    validator=self._validate_amount,
                    transformer=self._transform_amount
                ),
                Step(
                    id="handle",
                    type=StepType.TEXT,
                    message=lambda _: "Enter recipient handle:",
                    validator=self._validate_handle,
                    transformer=self._transform_handle
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_offer_confirmation,
                    validator=self._validate_button_response
                )
            ]
        elif self.flow_type == "cancel_credex":
            return [
                Step(
                    id="list",
                    type=StepType.LIST,
                    message=self._create_pending_offers_list,
                    validator=lambda x: x.startswith("cancel_"),
                    transformer=self._transform_cancel_selection
                ),
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_cancel_confirmation,
                    validator=self._validate_button_response
                )
            ]
        else:
            # Action flows (accept/decline) just need confirmation
            return [
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_action_confirmation,
                    validator=self._validate_button_response
                )
            ]

    def _validate_button_response(self, response: Dict[str, Any]) -> bool:
        """Validate button response from WhatsApp"""
        # Check message type
        if response.get("type") != "interactive":
            logger.debug("Message type is not interactive")
            return False

        # Get interactive data
        interactive = response.get("interactive", {})
        if not interactive:
            logger.debug("No interactive field in message")
            return False

        # Check interactive type
        if interactive.get("type") != "button_reply":
            logger.debug(f"Interactive type is not button_reply: {interactive.get('type')}")
            return False

        # Get button reply data
        button_reply = interactive.get("button_reply", {})
        if not button_reply:
            logger.debug("No button_reply in interactive message")
            return False

        # Check button ID
        button_id = button_reply.get("id")
        logger.debug(f"Received button ID: {button_id}")
        return button_id == "confirm_action"

    def _transform_cancel_selection(self, selection: str) -> Dict[str, Any]:
        """Transform cancel selection to get credex ID"""
        # Extract credex ID from selection (remove 'cancel_' prefix)
        credex_id = selection[7:] if selection.startswith("cancel_") else None
        logger.info(f"Extracted credex ID from selection: {credex_id}")

        if not credex_id:
            return {"error": "Invalid selection format"}

        # Find the offer in pending offers
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

    def _create_pending_offers_list(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create list of pending outgoing offers"""
        # Use pre-formatted pending offers from handler
        pending_offers = state.get("pending_offers", [])

        # Create rows for each offer
        rows = []
        for offer in pending_offers:
            rows.append({
                "id": f"cancel_{offer['id']}",
                "title": f"{offer['amount']} to {offer['to']}"
            })

        # Return interactive message with list
        message = "*Cancel Pending Outgoing Offers*\n\nSelect an offer to cancel:"
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": state.get("mobile_number"),
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": message
                },
                "action": {
                    "button": "🕹️ Options",
                    "sections": [
                        {
                            "title": "Pending Offers",
                            "rows": rows
                        }
                    ]
                }
            }
        }

    def _create_offer_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create confirmation message for offer flow"""
        amount = state["amount"]["amount"]
        denom = state["amount"]["denomination"]
        handle = state["handle"]["handle"]
        name = state["handle"]["name"]

        amount_str = self._format_amount(amount, denom)
        message = (
            f"Confirm transaction:\n\n"
            f"Amount: {amount_str}\n"
            f"To: {name} ({handle})"
        )

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": state.get("mobile_number"),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": message
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "confirm_action",
                                "title": "Confirm"
                            }
                        }
                    ]
                }
            }
        }

    def _create_cancel_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create confirmation message for canceling an offer"""
        credex_id = state.get("credex_id")
        if not credex_id:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": state.get("mobile_number"),
                "type": "text",
                "text": {
                    "body": "Missing credex ID"
                }
            }

        amount = state.get("amount")
        counterparty = state.get("counterparty")

        message = (
            f"*Cancel Credex Offer*\n\n"
            f"Amount: {amount}\n"
            f"To: {counterparty}"
        )

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": state.get("mobile_number"),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": message
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "confirm_action",
                                "title": "Cancel Offer"
                            }
                        }
                    ]
                }
            }
        }

    def _create_action_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create confirmation message for action flows"""
        amount = state.get("amount", "0.00")
        denomination = state.get("denomination", "USD")
        counterparty = state.get("counterparty", "Unknown")

        amount_str = self._format_amount(float(amount), denomination)

        messages = {
            "accept": f"Accept credex offer for {amount_str}\nFrom: {counterparty}",
            "decline": f"Decline credex offer for {amount_str}\nFrom: {counterparty}",
        }

        message = messages[self.flow_type]

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": state.get("mobile_number"),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": message
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "confirm_action",
                                "title": "Confirm"
                            }
                        }
                    ]
                }
            }
        }

    def _validate_amount(self, amount_str: str) -> bool:
        """Validate amount format"""
        if not amount_str:
            return False
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())
        if not match:
            return False
        denom = match.group(1) or match.group(4)
        return not denom or denom in self.VALID_DENOMINATIONS

    def _transform_amount(self, amount_str: str) -> Dict[str, Any]:
        """Transform amount to structured data"""
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())
        if match.group(1):  # Currency first format
            denom, amount = match.group(1), match.group(2)
        elif match.group(3):  # Amount first format
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
        account_id = data.get("accountID")
        name = data.get("accountName")

        if not account_id:
            return {"error": "Account not found"}

        return {
            "handle": handle,
            "account_id": account_id,
            "name": name or handle
        }

    def _format_amount(self, amount: float, denomination: str) -> str:
        """Format amount based on denomination"""
        if denomination in {"USD", "ZWG", "CAD"}:
            return f"${amount:.2f} {denomination}"
        elif denomination == "XAU":
            return f"{amount:.4f} {denomination}"
        return f"{amount} {denomination}"

    def _update_dashboard_state(self, response: Dict[str, Any]) -> None:
        """Update dashboard data in state from API response"""
        try:
            if not hasattr(self.credex_service, '_parent_service') or not hasattr(self.credex_service._parent_service, 'user'):
                logger.warning("Cannot update dashboard state: missing required service attributes")
                return

            # Get dashboard data from response
            dashboard = response.get("data", {}).get("dashboard")
            if dashboard is None:
                logger.warning("No dashboard data in response to update state with")
                return

            # Get current state
            user_state = self.credex_service._parent_service.user.state
            current_state = user_state.state
            current_profile = current_state.get("profile", {})

            # Update dashboard while preserving other profile data
            if "data" in current_profile:
                current_profile["data"]["dashboard"] = dashboard
            else:
                current_profile["data"] = {"dashboard": dashboard}

            # Update state
            user_state.update_state({
                "profile": current_profile
            }, "dashboard_update")

            logger.info(f"Successfully updated state with new dashboard data for {self.flow_type} operation")

        except Exception as e:
            logger.error(f"Failed to update dashboard state: {str(e)}")

    def complete(self) -> Union[str, Dict[str, Any]]:
        """Complete the flow"""
        try:
            if not self.credex_service:
                return "Service not initialized"

            if self.flow_type == "offer":
                return self._complete_offer()
            elif self.flow_type == "cancel_credex":
                return self._complete_cancel()
            else:
                return self._complete_action()

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            return str(e)

    def _complete_cancel(self) -> Union[str, Dict[str, Any]]:
        """Complete cancel flow"""
        if self.current_step.id == "confirm":
            # Execute cancellation
            credex_id = self.data.get("credex_id")
            if not credex_id:
                return "Missing credex ID"

            # Verify offer still exists
            pending_offers = self.data.get("pending_offers", [])
            offer_exists = any(
                offer["id"] == credex_id
                for offer in pending_offers
            )
            if not offer_exists:
                return "Selected offer is no longer available"

            success, response = self.credex_service.cancel_credex(credex_id)
            if not success:
                return response.get("message", "Failed to cancel offer")

            # Update dashboard state
            self._update_dashboard_state(response)

            # Show dashboard with success message
            dashboard_flow = DashboardFlow(success_message="Credex successfully cancelled")
            dashboard_flow.credex_service = self.credex_service
            dashboard_flow.data = {
                "mobile_number": self.data.get("mobile_number")
            }
            return dashboard_flow.complete()
        else:
            return self._create_pending_offers_list(self.data)

    def _complete_offer(self) -> Union[str, Dict[str, Any]]:
        """Complete offer flow"""
        # Create offer
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

        # Submit offer
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

        # Update dashboard state
        self._update_dashboard_state(response)

        # Show dashboard with success message
        dashboard_flow = DashboardFlow(success_message="Credex successfully offered")
        dashboard_flow.credex_service = self.credex_service
        dashboard_flow.data = {
            "mobile_number": self.data.get("mobile_number")
        }
        return dashboard_flow.complete()

    def _complete_action(self) -> Union[str, Dict[str, Any]]:
        """Complete action flow"""
        credex_id = self.kwargs.get("credex_id")
        if not credex_id:
            return "Missing credex ID"

        # Execute action
        if self.flow_type == "accept":
            success, response = self.credex_service.accept_credex(credex_id)
        elif self.flow_type == "decline":
            success, response = self.credex_service.decline_credex(credex_id)
        else:
            return f"Invalid action: {self.flow_type}"

        if not success:
            return response.get("message", f"Failed to {self.flow_type} offer")

        # Update dashboard state
        self._update_dashboard_state(response)

        # Show dashboard with success message
        dashboard_flow = DashboardFlow(success_message=f"Successfully {self.flow_type}ed credex offer")
        dashboard_flow.credex_service = self.credex_service
        dashboard_flow.data = {
            "mobile_number": self.data.get("mobile_number")
        }
        return dashboard_flow.complete()
