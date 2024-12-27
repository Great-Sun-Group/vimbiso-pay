"""Offer flow implementation"""
import logging
from typing import Any, Dict, List, Optional

from core.messaging.flow import FlowState, Step, StepType
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
            # Validate state has member_id before initialization
            if not state or not state.member_id:
                raise ValueError("State must include member_id")

            # Validate state data structure
            if not isinstance(state.data, dict):
                raise ValueError("State data must be dictionary")

            # Ensure channel info exists
            if "channel" not in state.data:
                raise ValueError("State missing channel info")

            # Create steps if not provided
            if steps is None:
                steps = self._create_steps(state)

            # Initialize base CredexFlow class with validated state
            super().__init__(
                id=id,
                steps=steps,
                flow_type=flow_type,
                state=state,
                **kwargs
            )

            # Get initialization context with validated member_id
            init_context = {
                "member_id": state.member_id,  # Now guaranteed to exist
                "channel": None,
                "flow_type": self.flow_type
            }

            # Add channel info if service is initialized
            if self.credex_service:
                try:
                    channel_id = self._get_channel_identifier()
                    if channel_id:
                        init_context["channel"] = {
                            "type": "whatsapp",
                            "identifier": channel_id
                        }
                except Exception as channel_error:
                    logger.warning(f"Could not get channel identifier: {str(channel_error)}")

            # Log successful initialization
            audit.log_flow_event(
                self.id,
                "initialization",
                None,
                init_context,
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

    def _create_steps(self, init_state: Optional[FlowState] = None) -> List[Step]:
        """Create steps for offer flow

        Args:
            init_state: Optional initial state during initialization

        Note:
            During initialization, self.state is not yet set, so we use init_state
            After initialization, self.state will be available
        """
        def get_handle_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
            """Get handle prompt with proper state access"""
            flow_state = self.state.to_dict() if self.state else init_state.to_dict() if init_state else {"member_id": None}
            return CredexTemplates.create_handle_prompt(
                self._get_channel_identifier(),
                flow_state
            )

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
                message=get_handle_prompt,
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

            # Get member ID from flow state - SINGLE SOURCE OF TRUTH
            if not self.state or not self.state.member_id:
                raise ValueError("Missing member ID in flow state")

            channel_id = self._get_channel_identifier()
            if not channel_id:
                raise ValueError("Missing channel identifier")

            # Log completion attempt with member context
            audit_context = {
                "member_id": self.state.member_id,  # From flow state
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
                "authorizer_member_id": self.state.member_id,  # From flow state
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
