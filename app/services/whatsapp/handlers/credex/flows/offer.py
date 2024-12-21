"""Offer flow implementation"""
import logging
from typing import Any, Dict, List, Union

from core.messaging.flow import Step, StepType

from ..templates import CredexTemplates
from .base import CredexFlow

logger = logging.getLogger(__name__)


class OfferFlow(CredexFlow):
    """Flow for creating a new credex offer"""

    def __init__(self, flow_type: str = None, state: Dict = None, **kwargs):
        # Default to "offer" if not provided
        if flow_type is None and (state is None or "flow_type" not in state.get("flow_data", {})):
            flow_type = "offer"
        super().__init__(flow_type=flow_type, state=state, **kwargs)

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
                message=lambda s: CredexTemplates.create_handle_prompt(
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

    def _transform_handle(self, handle: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Transform handle and validate with API"""
        # First validate format using parent method
        if not super()._validate_handle(handle):
            raise ValueError("Invalid handle format")

        # Extract handle text
        if isinstance(handle, dict):
            interactive = handle.get("interactive", {})
            if interactive.get("type") == "text":
                handle = interactive.get("text", {}).get("body", "")
            else:
                raise ValueError("Invalid handle format")

        handle = handle.strip()

        # Make API call to validate handle
        success, response = self.credex_service._member.validate_handle(handle)
        if not success:
            raise ValueError(response.get("message", "Invalid handle"))

        # Get account data
        data = response.get("data", {})
        if not data or not data.get("accountID"):
            raise ValueError("Invalid account data received from API")

        # Store validated handle data for confirmation step
        return {
            "handle": handle,
            "account_id": data.get("accountID"),
            "name": data.get("accountName", handle),
            "_validation_success": True
        }

    def complete(self) -> Dict[str, Any]:
        """Complete the offer flow by making the offer API call"""
        try:
            # Prepare offer data
            amount_data = self.data.get("amount_denom", {})
            handle_data = self.data.get("handle", {})

            if not amount_data or not handle_data:
                return {
                    "success": False,
                    "message": "Missing required offer data"
                }

            # Make API call to create offer
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

            if not success:
                return {
                    "success": False,
                    "message": response.get("message", "Offer failed"),
                    "response": response
                }

            # Update dashboard with successful response
            self._update_dashboard(response)

            # Get success message from response
            action = response.get("data", {}).get("action", {})
            message = (
                action.get("message") or  # Try direct message
                action.get("details", {}).get("message") or  # Try details.message
                "CredEx offer created successfully"  # Default message
            )

            return {
                "success": True,
                "message": message,
                "response": response
            }

        except Exception as e:
            logger.error(f"Error completing offer: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }
