"""Offer flow implementation"""
import logging
from typing import Any, Dict, List, Union

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

        # Initialize state structure
        if state and isinstance(state, dict):
            # Ensure state has required flow fields
            if "flow_data" not in state:
                state["flow_data"] = {}

            flow_data = state["flow_data"]
            if not isinstance(flow_data, dict):
                flow_data = {}

            # Extract member ID for flow ID
            member_id = state.get("member_id")
            if not member_id:
                raise ValueError("Missing member ID in state")

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
            mobile_number = state.get("mobile_number")
            account_id = state.get("account_id")

            if not mobile_number or not account_id:
                raise ValueError("Missing required fields: mobile_number and account_id")

            # Initialize data structure
            data = {
                "mobile_number": mobile_number,
                "member_id": member_id,
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

            # Update state with required fields
            state.update({
                "id": flow_id,
                "step": flow_data["step"],
                "data": data,
                "flow_data": flow_data,  # Include complete flow_data structure
                "mobile_number": mobile_number,
                "_validation_context": validation_context["_validation_context"],
                "_validation_state": validation_context["_validation_state"],
                "_last_updated": audit.get_current_timestamp(),
                # Ensure these fields are always present
                "authenticated": state.get("authenticated", False),
                "_version": state.get("_version", 1),
                "_stage": state.get("_stage"),
                "_option": state.get("_option"),
                "_direction": state.get("_direction")
            })

            # Ensure flow_data.data has required fields
            flow_data["data"].update({
                "flow_type": normalized_flow_type,
                "id": flow_id,
                "step": flow_data["step"]
            })

            # Validate required fields in state and flow_data
            required_fields = ["id", "step", "data"]

            # Check root state
            missing_state_fields = [field for field in required_fields if field not in state]
            if missing_state_fields:
                error_msg = f"Missing required flow fields in state: {', '.join(missing_state_fields)}"
                logger.error(error_msg)
                audit.log_flow_event(
                    flow_id,
                    "initialization_error",
                    None,
                    state,
                    "failure",
                    error_msg
                )
                raise ValueError(error_msg)

            # Check flow_data structure
            missing_flow_data_fields = [field for field in required_fields if field not in flow_data]
            if missing_flow_data_fields:
                error_msg = f"Missing required flow fields in flow_data: {', '.join(missing_flow_data_fields)}"
                logger.error(error_msg)
                audit.log_flow_event(
                    flow_id,
                    "initialization_error",
                    None,
                    state,
                    "failure",
                    error_msg
                )
                raise ValueError(error_msg)

            # Check flow_data.data structure
            flow_data_required_fields = ["flow_type", "id", "step", "mobile_number", "member_id", "account_id"]
            missing_data_fields = [field for field in flow_data_required_fields if field not in flow_data.get("data", {})]
            if missing_data_fields:
                error_msg = f"Missing required fields in flow_data.data: {', '.join(missing_data_fields)}"
                logger.error(error_msg)
                audit.log_flow_event(
                    flow_id,
                    "initialization_error",
                    None,
                    state,
                    "failure",
                    error_msg
                )
                raise ValueError(error_msg)

            # Store old state for transition logging
            old_state = state.copy()

            # Log state transition
            audit.log_state_transition(
                flow_id,
                old_state,
                state,
                "success"
            )

            # Log flow initialization event
            audit.log_flow_event(
                flow_id,
                "initialization",
                None,
                state,
                "success"
            )

            # Log detailed debug information
            logger.debug("[OfferFlow] Initializing with state")
            logger.debug("- State keys: %s", list(state.keys()))
            logger.debug("- Flow data: %s", flow_data)
            logger.debug("- Flow ID: %s", flow_id)
            logger.debug("- Core fields: %s", {
                "mobile_number": state.get("mobile_number"),
                "member_id": state.get("member_id"),
                "account_id": state.get("account_id")
            })
            logger.debug("- Validation context: %s", validation_context)

        try:
            # Initialize base CredexFlow class with flow type and state
            super().__init__(flow_type=self.flow_type, state=state)

            # Ensure validation context is preserved after parent initialization
            if validation_context:
                self.data.update({
                    "_validation_context": validation_context["_validation_context"],
                    "_validation_state": validation_context["_validation_state"]
                })

                # Log validation context preservation
                audit.log_validation_event(
                    flow_id,
                    "initialization",
                    validation_context,
                    True,
                    "Validation context preserved after initialization"
                )

            # Log successful initialization
            logger.debug("[OfferFlow] Post-init data keys: %s", list(self.data.keys()))
            logger.debug("[OfferFlow] Post-init flow state: %s", self.get_state())

        except Exception as e:
            # Log initialization error
            error_msg = f"Flow initialization error: {str(e)}"
            logger.error(error_msg)
            audit.log_flow_event(
                flow_id if 'flow_id' in locals() else 'unknown',
                "initialization_error",
                None,
                state or {},
                "failure",
                error_msg
            )
            raise

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
        flow_id = self.data.get("_flow_id", "unknown")

        try:
            # First validate format using parent method
            if not super()._validate_handle(handle):
                audit.log_validation_event(
                    flow_id,
                    "handle_validation",
                    handle,
                    False,
                    "Invalid handle format"
                )
                raise ValueError("Invalid handle format")

            # Extract handle text
            if isinstance(handle, dict):
                interactive = handle.get("interactive", {})
                if interactive.get("type") == "text":
                    handle = interactive.get("text", {}).get("body", "")
                else:
                    audit.log_validation_event(
                        flow_id,
                        "handle_validation",
                        handle,
                        False,
                        "Invalid interactive format"
                    )
                    raise ValueError("Invalid handle format")

            handle = handle.strip()

            # Log API validation attempt
            audit.log_flow_event(
                flow_id,
                "handle_api_validation",
                "handle",
                {"handle": handle},
                "in_progress"
            )

            # Make API call to validate handle
            success, response = self.credex_service._member.validate_handle(handle)
            if not success:
                error_msg = response.get("message", "Invalid handle")
                audit.log_validation_event(
                    flow_id,
                    "handle_api_validation",
                    handle,
                    False,
                    error_msg
                )
                raise ValueError(error_msg)

            # Get account data
            data = response.get("data", {})
            if not data or not data.get("accountID"):
                error_msg = "Invalid account data received from API"
                audit.log_validation_event(
                    flow_id,
                    "handle_api_validation",
                    handle,
                    False,
                    error_msg
                )
                raise ValueError(error_msg)

            # Create validated result
            result = {
                "handle": handle,
                "account_id": data.get("accountID"),
                "name": data.get("accountName", handle),
                "_validation_success": True
            }

            # Log successful validation
            audit.log_validation_event(
                flow_id,
                "handle_validation",
                result,
                True,
                "Handle validated successfully"
            )

            return result

        except Exception as e:
            error_msg = f"Handle validation error: {str(e)}"
            logger.error(error_msg)

            # Log validation error if not already logged
            if not str(e).startswith("Invalid"):
                audit.log_validation_event(
                    flow_id,
                    "handle_validation",
                    handle,
                    False,
                    error_msg
                )

            raise ValueError(error_msg)

    def complete(self) -> Dict[str, Any]:
        """Complete the offer flow by making the offer API call"""
        flow_id = self.data.get("_flow_id", "unknown")

        try:
            # Prepare offer data
            amount_data = self.data.get("amount_denom", {})
            handle_data = self.data.get("handle", {})

            if not amount_data or not handle_data:
                error_msg = "Missing required offer data"
                audit.log_flow_event(
                    flow_id,
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

            # Log completion attempt
            audit.log_flow_event(
                flow_id,
                "completion_start",
                None,
                self.data,
                "in_progress"
            )

            # Prepare offer payload
            offer_payload = {
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
            }

            # Log offer attempt
            audit.log_validation_event(
                flow_id,
                "offer_creation",
                offer_payload,
                True,
                "Attempting to create offer"
            )

            # Make API call to create offer
            success, response = self.credex_service.offer_credex(offer_payload)

            if not success:
                error_msg = response.get("message", "Offer failed")
                audit.log_flow_event(
                    flow_id,
                    "offer_creation_error",
                    None,
                    self.data,
                    "failure",
                    error_msg
                )
                return {
                    "success": False,
                    "message": error_msg,
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

            # Log successful completion
            audit.log_flow_event(
                flow_id,
                "completion_success",
                None,
                self.data,
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
                flow_id,
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
