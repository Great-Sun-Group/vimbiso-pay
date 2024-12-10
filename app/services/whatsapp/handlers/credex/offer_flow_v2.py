"""Progressive implementation of the credex offer flow"""
import logging
import re
from typing import Any, Dict, Optional

from core.messaging.flow import Flow, Step, StepType
from core.messaging.templates import ProgressiveInput, ListSelection, ButtonSelection
from core.messaging.types import Message as WhatsAppMessage
from core.transactions import TransactionOffer, TransactionType
from services.state.service import StateStage

logger = logging.getLogger(__name__)


class CredexOfferFlow(Flow):
    """Progressive flow for creating credex offers"""

    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s+)?(\d+(?:\.\d+)?)$')

    def __init__(self, id: str, steps: list):
        super().__init__(id, self._create_steps())
        self.transaction_service = None  # Should be injected

    def _create_steps(self) -> list[Step]:
        """Create flow steps"""
        return [
            # Step 1: Amount Input
            Step(
                id="amount",
                type=StepType.TEXT_INPUT,
                stage=StateStage.CREDEX.value,
                message=ProgressiveInput.create_prompt(
                    "Enter amount in USD or specify denomination:",
                    [
                        "100 (USD)",
                        "ZWG 100",
                        "XAU 1"
                    ]
                ),
                validation=self._validate_amount,
                transform=self._transform_amount
            ),

            # Step 2: Amount Confirmation
            Step(
                id="amount_confirmation",
                type=StepType.BUTTON_SELECT,
                stage=StateStage.CREDEX.value,
                message=self._create_amount_confirmation_message,
                condition=lambda state: "amount" in state and "denomination" in state
            ),

            # Step 3: Recipient Selection
            Step(
                id="recipient",
                type=StepType.LIST_SELECT,
                stage=StateStage.CREDEX.value,
                message=self._create_recipient_selection_message,
                condition=lambda state: state.get("amount_confirmed") == "confirm"
            ),

            # Step 4: New Recipient Input (conditional)
            Step(
                id="new_recipient",
                type=StepType.TEXT_INPUT,
                stage=StateStage.CREDEX.value,
                message=ProgressiveInput.create_prompt(
                    "Enter recipient's handle:",
                    ["@username"]
                ),
                validation=self._validate_handle,
                condition=lambda state: state.get("recipient") == "new"
            ),

            # Step 5: Final Confirmation
            Step(
                id="confirm",
                type=StepType.BUTTON_SELECT,
                stage=StateStage.CREDEX.value,
                message=self._create_final_confirmation_message,
                condition=lambda state: self._can_show_confirmation(state)
            )
        ]

    def _validate_amount(self, amount_str: str) -> bool:
        """Validate amount string format"""
        if not amount_str:
            return False
        match = self.AMOUNT_PATTERN.match(amount_str.strip().upper())
        if not match:
            return False
        denom = match.group(1)
        if denom and denom not in self.VALID_DENOMINATIONS:
            return False
        return True

    def _transform_amount(self, amount_str: str) -> Dict[str, Any]:
        """Transform amount string to amount and denomination"""
        amount_str = amount_str.strip().upper()
        match = self.AMOUNT_PATTERN.match(amount_str)
        denom, amount = match.groups()
        return {
            "amount": float(amount),
            "denomination": denom or "USD"
        }

    def _validate_handle(self, handle: str) -> bool:
        """Validate recipient handle"""
        return bool(handle and handle.startswith("@"))

    def _create_amount_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Create amount confirmation message"""
        amount = state.get("amount")
        denomination = state.get("denomination", "USD")
        return ButtonSelection.create_buttons({
            "text": f"Confirm amount: {denomination} {amount}",
            "buttons": [
                {"id": "confirm", "title": "Confirm"},
                {"id": "retry", "title": "Try Again"}
            ]
        })

    def _create_recipient_selection_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Create recipient selection message"""
        # This would typically fetch recent recipients from a service
        recent_recipients = [
            {"id": "recent_1", "title": "@user1", "description": "Recent transaction"},
            {"id": "recent_2", "title": "@user2", "description": "Recent transaction"}
        ]

        return ListSelection.create_list({
            "title": "Select Recipient",
            "sections": [
                {
                    "title": "Recent",
                    "items": recent_recipients
                },
                {
                    "title": "Options",
                    "items": [
                        {"id": "new", "title": "New Recipient"}
                    ]
                }
            ]
        })

    def _create_final_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Create final confirmation message"""
        amount = state.get("amount")
        denomination = state.get("denomination")
        recipient = state.get("new_recipient") or state.get("recipient")

        return ButtonSelection.create_buttons({
            "text": f"Send {denomination} {amount} to {recipient}?",
            "buttons": [
                {"id": "confirm", "title": "Confirm"},
                {"id": "cancel", "title": "Cancel"}
            ]
        })

    def _can_show_confirmation(self, state: Dict[str, Any]) -> bool:
        """Check if we can show final confirmation"""
        has_amount = "amount" in state and "denomination" in state
        has_recipient = "recipient" in state
        if state.get("recipient") == "new":
            return has_amount and "new_recipient" in state
        return has_amount and has_recipient

    def create_transaction(self) -> Optional[TransactionOffer]:
        """Create transaction offer from flow state"""
        if not self._can_show_confirmation(self.state):
            return None

        # Create transaction offer
        return TransactionOffer(
            authorizer_member_id=self.state["authorizer_member_id"],
            issuer_member_id=self.state["issuer_member_id"],
            receiver_account_id=self.state["receiver_account_id"],
            amount=self.state["amount"],
            denomination=self.state["denomination"],
            type=TransactionType.SECURED_CREDEX,
            handle=self.state.get("new_recipient") or self.state["recipient"],
            metadata={"full_name": self.state.get("recipient_name", "")}
        )

    @classmethod
    def get_flow_by_id(cls, flow_id: str) -> Optional[Flow]:
        """Get flow instance by ID"""
        if flow_id == "credex_offer":
            return cls(flow_id, [])
        return None
