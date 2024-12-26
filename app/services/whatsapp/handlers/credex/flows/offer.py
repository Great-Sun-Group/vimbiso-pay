"""Offer flow implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.flow import Step, StepType, FlowState
from core.utils.flow_audit import FlowAuditLogger

from ..templates import CredexTemplates
from .base import CredexFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class OfferFlow(CredexFlow):
    """Flow for creating a new credex offer"""

    def __init__(self, id: str, steps: List[Step] = None, flow_type: str = "offer", state: Optional[FlowState] = None, **kwargs):
        """Initialize offer flow"""
        try:
            # Create steps if not provided
            if steps is None:
                steps = self._create_steps()

            # Initialize base CredexFlow class
            super().__init__(
                id=id,
                steps=steps,
                flow_type=flow_type,
                state=state,
                **kwargs
            )

            # Get member ID from state if available
            member_id = state.member_id if state else None
            channel = {"type": "whatsapp", "identifier": self._get_channel_identifier()} if self.credex_service else None

            # Log successful initialization
            audit.log_flow_event(
                self.id,
                "initialization",
                None,
                {
                    "member_id": member_id,
                    "channel": channel,
                    "flow_type": self.flow_type
                },
                "success"
            )

        except Exception as e:
            # Log initialization error
            error_msg = f"Flow initialization error: {str(e)}"
            logger.error(error_msg)
            audit.log_flow_event(
                id,  # Use provided ID instead of flow_id
                "initialization_error",
                None,
                {
                    "error": error_msg,
                    "flow_type": flow_type
                },
                "failure"
            )
            raise

    def _get_channel_identifier_from_state(self, state: Dict) -> str:
        """Get channel identifier from state using StateManager"""
        from services.whatsapp.state_manager import StateManager
        return StateManager.get_channel_identifier(state)

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
                    self._get_channel_identifier()
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
        """Complete the offer flow by making the offer API call"""
        try:
            # Get required data
            amount_data = self.data.get("amount_denom", {})
            handle_data = self.data.get("handle", {})

            if not amount_data or not handle_data:
                error_msg = "Missing required offer data"
                audit.log_flow_event(
                    self.id,
                    "completion_error",
                    None,
                    self.data,
                    "failure",
                    error_msg
                )
                return {
                    "success": False,
                    "message": error_msg
                }

            # Get member ID and channel info from top level state - SINGLE SOURCE OF TRUTH
            current_state = self.credex_service._parent_service.user.state.state
            member_id = current_state.get("member_id")
            if not member_id:
                raise ValueError("Missing member ID in state")

            channel_id = self._get_channel_identifier()
            if not channel_id:
                raise ValueError("Missing channel identifier")

            # Log completion attempt with member context
            audit_context = {
                "member_id": member_id,
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                },
                "amount": amount_data,
                "handle": handle_data
            }
            audit.log_flow_event(
                self.id,
                "completion_start",
                None,
                audit_context,
                "in_progress"
            )

            # Prepare offer payload with member context
            offer_payload = {
                "authorizer_member_id": member_id,
                "issuerAccountID": self.data.get("account_id"),
                "receiverAccountID": handle_data.get("account_id"),
                "InitialAmount": amount_data.get("amount", 0),
                "Denomination": amount_data.get("denomination", "USD"),
                "credexType": "PURCHASE",
                "OFFERSorREQUESTS": "OFFERS",
                "securedCredex": True,
                "handle": handle_data.get("handle"),
                "metadata": {
                    "name": handle_data.get("name"),
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id
                    }
                }
            }

            # Make API call to create offer
            success, response = self.credex_service.offer_credex(offer_payload)

            if not success:
                error_msg = response.get("message", "Offer failed")
                audit.log_flow_event(
                    self.id,
                    "offer_creation_error",
                    None,
                    {**audit_context, "error": error_msg},
                    "failure"
                )
                return {
                    "success": False,
                    "message": error_msg,
                    "response": response
                }

            # Update dashboard with member-centric state
            self._update_dashboard(response)

            # Get success message from response
            action = response.get("data", {}).get("action", {})
            message = (
                action.get("message") or  # Try direct message
                action.get("details", {}).get("message") or  # Try details.message
                "CredEx offer created successfully"  # Default message
            )

            # Log successful completion
            audit.log_flow_event(
                self.id,
                "completion_success",
                None,
                {**audit_context, "response": response},
                "success",
                message
            )

            return {
                "success": True,
                "message": message,
                "response": response
            }

        except Exception as e:
            error_msg = f"Error completing offer: {str(e)}"
            logger.error(error_msg)

            # Log error with full context
            audit.log_flow_event(
                self.id,
                "completion_error",
                None,
                self.data,
                "failure",
                error_msg
            )

            return {
                "success": False,
                "message": error_msg
            }
