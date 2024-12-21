"""Offer flow implementation"""
import logging
from typing import Any, Dict, List

from core.messaging.flow import Step, StepType

from .base import CredexFlow

logger = logging.getLogger(__name__)


class OfferFlow(CredexFlow):
    """Flow for creating a new credex offer"""

    def __init__(self, **kwargs):
        super().__init__("offer", **kwargs)

    def _create_steps(self) -> List[Step]:
        """Create steps for offer flow"""
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
                message=lambda s: self.templates.create_handle_prompt(
                    self.data.get("mobile_number")
                ),
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

    def complete(self) -> Dict[str, Any]:
        """Complete the offer flow"""
        try:
            # Prepare offer data
            amount_data = self.data.get("amount_denom", {})
            handle_data = self.data.get("handle", {})

            if not amount_data or not handle_data:
                return {
                    "success": False,
                    "message": "Missing required offer data"
                }

            # Make API call
            success, response = self.credex_service.offer_credex({
                "authorizer_member_id": self.data.get("member_id"),
                "issuerAccountID": self.data.get("account_id"),
                "receiverAccountID": handle_data.get("account_id"),
                "InitialAmount": amount_data.get("amount", 0),
                "Denomination": amount_data.get("denomination", "USD"),
                "credexType": "PURCHASE",
                "OFFERSorREQUESTS": "OFFERS",
                "securedCredex": True,
                "handle": handle_data.get("handle"),
                "metadata": {"name": handle_data.get("name")}
            })

            # Return structured response with API result
            if success:
                self._update_dashboard(response)
                return {
                    "success": True,
                    "message": "Credex successfully offered",
                    "response": response
                }

            return {
                "success": False,
                "message": response.get("message", "Offer failed"),
                "response": response
            }

        except Exception as e:
            logger.error(f"Error completing offer: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }
