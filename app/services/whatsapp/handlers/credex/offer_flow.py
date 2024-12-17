"""Clean implementation of credex offer flow"""
import logging
import re
from typing import Dict, Any, Optional

from core.messaging.flow import Flow, Step, StepType
from core.transactions import TransactionOffer, TransactionType

logger = logging.getLogger(__name__)


class CredexOfferFlow(Flow):
    """Simplified credex offer flow"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s+)?(\d+(?:\.\d+)?)$')
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

    def __init__(self):
        steps = [
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
                message=self._create_confirmation,
                validator=lambda x: x == "confirm"
            )
        ]
        super().__init__("credex_offer", steps)
        self.credex_service = None

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

    def _create_confirmation(self, state: Dict[str, Any]) -> str:
        """Create confirmation message"""
        amount = state["amount"]["amount"]
        denom = state["amount"]["denomination"]
        handle = state["handle"]["handle"]
        name = state["handle"]["name"]

        amount_str = (
            f"${amount:.2f} {denom}"
            if denom in {"USD", "ZWG", "CAD"}
            else f"{amount:.4f} {denom}"
            if denom == "XAU"
            else f"{amount} {denom}"
        )

        return (
            f"Confirm transaction:\n\n"
            f"Amount: {amount_str}\n"
            f"To: {name} ({handle})\n\n"
            f"[confirm] Send"
        )

    def complete(self) -> Optional[str]:
        """Complete transaction"""
        try:
            if not self.credex_service:
                raise ValueError("Service not initialized")

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

            return "Transaction complete"

        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            return f"Error: {str(e)}"
