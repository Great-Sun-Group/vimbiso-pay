"""Unified credex flow implementation"""
import logging
import re
from typing import Dict, Any, List

from core.messaging.flow import Flow, Step, StepType
from core.transactions import TransactionOffer, TransactionType

logger = logging.getLogger(__name__)


class CredexFlow(Flow):
    """Base class for all credex flows"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s+)?(\d+(?:\.\d+)?)$')
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

    def __init__(self, flow_type: str, **kwargs):
        """Initialize flow

        Args:
            flow_type: Type of flow ('offer', 'accept', 'decline', 'cancel')
            **kwargs: Flow-specific arguments (e.g. credex_id for actions)
        """
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
                    validator=lambda x: x == "confirm"
                )
            ]
        else:
            # Action flows (accept/decline/cancel) just need confirmation
            return [
                Step(
                    id="confirm",
                    type=StepType.BUTTON,
                    message=self._create_action_confirmation,
                    validator=lambda x: x == "confirm"
                )
            ]

    def _validate_amount(self, amount_str: str) -> bool:
        """Validate amount format"""
        if not amount_str:
            return False
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())
        if not match:
            return False
        denom = match.group(1)
        return not denom or denom in self.VALID_DENOMINATIONS

    def _transform_amount(self, amount_str: str) -> Dict[str, Any]:
        """Transform amount to structured data"""
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())
        denom, amount = match.groups()
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
            raise ValueError("Service not initialized")

        handle = handle.strip()
        success, response = self.credex_service._member.validate_handle(handle)
        if not success:
            raise ValueError(response.get("message", "Invalid handle"))

        data = response.get("data", {})
        account_id = data.get("accountID")
        name = data.get("accountName")

        if not account_id:
            raise ValueError("Account not found")

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

    def _create_offer_confirmation(self, state: Dict[str, Any]) -> str:
        """Create confirmation message for offer flow"""
        amount = state["amount"]["amount"]
        denom = state["amount"]["denomination"]
        handle = state["handle"]["handle"]
        name = state["handle"]["name"]

        amount_str = self._format_amount(amount, denom)

        return (
            f"Confirm transaction:\n\n"
            f"Amount: {amount_str}\n"
            f"To: {name} ({handle})\n\n"
            f"[confirm] Send"
        )

    def _create_action_confirmation(self, state: Dict[str, Any]) -> str:
        """Create confirmation message for action flows"""
        amount = state.get("amount", "0.00")
        denomination = state.get("denomination", "USD")
        counterparty = state.get("counterparty", "Unknown")

        amount_str = self._format_amount(float(amount), denomination)

        messages = {
            "accept": f"Accept credex offer for {amount_str}\nFrom: {counterparty}",
            "decline": f"Decline credex offer for {amount_str}\nFrom: {counterparty}",
            "cancel": f"Cancel credex offer for {amount_str}\nTo: {counterparty}"
        }

        return (
            f"{messages[self.flow_type]}\n\n"
            "[confirm] Confirm"
        )

    def complete(self) -> str:
        """Complete the flow"""
        try:
            if not self.credex_service:
                raise ValueError("Service not initialized")

            if self.flow_type == "offer":
                return self._complete_offer()
            else:
                return self._complete_action()

        except Exception as e:
            logger.error(f"Flow completion error: {str(e)}")
            raise ValueError(str(e))

    def _complete_offer(self) -> str:
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
            raise ValueError(response.get("message", "Offer failed"))

        # Extract dashboard data from response and update state
        if hasattr(self.credex_service, '_parent_service') and hasattr(self.credex_service._parent_service, 'user'):
            # Get current profile to preserve non-dashboard data
            current_state = self.credex_service._parent_service.user.state.state
            current_profile = current_state.get("profile", {})

            # Update dashboard data while preserving other profile data
            if "data" in current_profile:
                current_profile["data"]["dashboard"] = response.get("data", {}).get("dashboard")
            else:
                current_profile["data"] = {
                    "dashboard": response.get("data", {}).get("dashboard")
                }

            # Update state with merged profile data
            self.credex_service._parent_service.user.state.update_state({
                "profile": current_profile
            }, "dashboard_update")
            logger.debug("Updated state with fresh dashboard data")

        return "Credex offered successfully."

    def _complete_action(self) -> str:
        """Complete action flow"""
        credex_id = self.kwargs.get("credex_id")
        if not credex_id:
            raise ValueError("Missing credex ID")

        # Execute action
        if self.flow_type == "accept":
            success, response = self.credex_service.accept_credex(credex_id)
        elif self.flow_type == "decline":
            success, response = self.credex_service.decline_credex(credex_id)
        elif self.flow_type == "cancel":
            success, response = self.credex_service.cancel_credex(credex_id)
        else:
            raise ValueError(f"Invalid action: {self.flow_type}")

        if not success:
            raise ValueError(response.get("message", f"Failed to {self.flow_type} offer"))

        # Extract dashboard data from response and update state
        if hasattr(self.credex_service, '_parent_service') and hasattr(self.credex_service._parent_service, 'user'):
            # Get current profile to preserve non-dashboard data
            current_state = self.credex_service._parent_service.user.state.state
            current_profile = current_state.get("profile", {})

            # Update dashboard data while preserving other profile data
            if "data" in current_profile:
                current_profile["data"]["dashboard"] = response.get("data", {}).get("dashboard")
            else:
                current_profile["data"] = {
                    "dashboard": response.get("data", {}).get("dashboard")
                }

            # Update state with merged profile data
            self.credex_service._parent_service.user.state.update_state({
                "profile": current_profile
            }, "dashboard_update")
            logger.debug("Updated state with fresh dashboard data")

        return f"Successfully {self.flow_type}ed credex offer"
