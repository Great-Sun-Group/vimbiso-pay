"""Offer flow implementation"""
import logging
from typing import Any, Dict, List

from core.messaging.flow import Step, StepType
from core.utils.flow_audit import FlowAuditLogger

from ..templates import CredexTemplates
from .base import CredexFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class OfferFlow(CredexFlow):
    """Flow for creating a new credex offer"""

    def __init__(self, flow_type: str = "offer", state: Dict = None, **kwargs):
        """Initialize offer flow"""
        # Store flow_type for parent class
        self.flow_type = flow_type

        # Initialize base state if none provided
        if state is None:
            state = {}

        # Get member ID and channel info from top level - SINGLE SOURCE OF TRUTH
        member_id = state.get("member_id")
        if not member_id:
            raise ValueError("Missing member ID")

        channel_id = self._get_channel_identifier_from_state(state)
        if not channel_id:
            raise ValueError("Missing channel identifier")

        # Initialize state structure
        if state and isinstance(state, dict):
            # Ensure state has required flow fields
            if "flow_data" not in state:
                state["flow_data"] = {}

            flow_data = state["flow_data"]
            if not isinstance(flow_data, dict):
                flow_data = {}

            # Normalize flow type and create flow ID
            normalized_flow_type = flow_type or "offer"
            flow_id = f"{normalized_flow_type}_{member_id}"

            # Initialize validation context structure
            validation_context = {
                "_validation_context": {},
                "_validation_state": {}
            }

            # Preserve existing context from both state and flow data
            if isinstance(state.get("_validation_context"), dict):
                validation_context["_validation_context"].update(state["_validation_context"])
            if isinstance(state.get("_validation_state"), dict):
                validation_context["_validation_state"].update(state["_validation_state"])

            flow_data_context = flow_data.get("data", {}).get("_validation_context", {})
            flow_data_state = flow_data.get("data", {}).get("_validation_state", {})
            if isinstance(flow_data_context, dict):
                validation_context["_validation_context"].update(flow_data_context)
            if isinstance(flow_data_state, dict):
                validation_context["_validation_state"].update(flow_data_state)

            # Get required fields from state
            account_id = state.get("account_id")
            if not account_id:
                raise ValueError("Missing account ID")

            # Initialize data structure with proper state management
            data = {
                "account_id": account_id,
                "flow_type": normalized_flow_type,
                "_validation_context": validation_context["_validation_context"],
                "_validation_state": validation_context["_validation_state"],
                "amount_denom": {
                    "amount": 0,
                    "denomination": "USD"
                }
            }

            # Initialize flow_data structure with required fields
            flow_data = {
                "id": flow_id,
                "step": state.get("step", 0),  # Preserve step if exists
                "data": data,
                "flow_type": normalized_flow_type,
                "_previous_data": state.get("_previous_data", {})
            }

            # Update state with member-centric structure
            new_state = {
                # Core identity at top level - SINGLE SOURCE OF TRUTH
                "member_id": member_id,  # Primary identifier

                # Channel info at top level - SINGLE SOURCE OF TRUTH
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_id
                },

                # Flow and state info
                "id": flow_id,
                "step": flow_data["step"],
                "data": data,
                "flow_data": flow_data,
                "authenticated": state.get("authenticated", False),
                "account_id": account_id,

                # Validation context
                "_validation_context": validation_context["_validation_context"],
                "_validation_state": validation_context["_validation_state"],
                "_last_updated": audit.get_current_timestamp(),

                # Preserve additional state fields
                "_version": state.get("_version", 1),
                "_stage": state.get("_stage"),
                "_option": state.get("_option"),
                "_direction": state.get("_direction")
            }

            # Log state preparation
            logger.debug("[OfferFlow] Preparing new state:")
            logger.debug("- State keys: %s", list(new_state.keys()))
            logger.debug("- Flow data: %s", flow_data)
            logger.debug("- Flow ID: %s", flow_id)
            logger.debug("- Core fields: %s", {
                "member_id": member_id,
                "channel": new_state["channel"],
                "account_id": account_id
            })

            # Log state transition
            audit.log_state_transition(
                flow_id,
                state,
                new_state,
                "success"
            )

            # Update state with new structure
            state = new_state

        try:
            # Initialize base CredexFlow class
            super().__init__(flow_type=self.flow_type, state=state)

            # Log successful initialization
            audit.log_flow_event(
                self.id,
                "initialization",
                None,
                {
                    "member_id": member_id,
                    "channel": state.get("channel"),
                    "flow_type": self.flow_type
                },
                "success"
            )

        except Exception as e:
            # Log initialization error
            error_msg = f"Flow initialization error: {str(e)}"
            logger.error(error_msg)
            audit.log_flow_event(
                flow_id if 'flow_id' in locals() else 'unknown',
                "initialization_error",
                None,
                {
                    "member_id": member_id,
                    "channel": state.get("channel") if state else None,
                    "error": error_msg
                },
                "failure"
            )
            raise

    def _get_channel_identifier_from_state(self, state: Dict) -> str:
        """Get channel identifier from state

        Args:
            state: The state dictionary

        Returns:
            str: The channel identifier from top level state.channel

        Note:
            Channel info is only stored at top level state.channel
            as the single source of truth
        """
        return state.get("channel", {}).get("identifier")

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
