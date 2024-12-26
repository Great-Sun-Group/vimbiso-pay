"""Clean flow management implementation"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


@dataclass
class FlowState:
    """Flow state with member-centric design

    Attributes:
        id: Unique flow identifier
        member_id: Member ID (from top level state - SINGLE SOURCE OF TRUTH)
        step: Current step index
        data: Flow data dictionary containing:
            - flow_type: Type of flow
            - _validation_context: Validation context
            - _validation_state: Validation state

    Note:
        - member_id comes from top level state as SINGLE SOURCE OF TRUTH
        - channel info comes from top level state
        - No duplication of member_id or channel info in flow_data
    """
    id: str
    member_id: str  # From top level state - SINGLE SOURCE OF TRUTH
    step: int = 0
    data: Dict[str, Any] = field(default_factory=lambda: {
        "flow_type": None,
        "_validation_context": {},
        "_validation_state": {}
    })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization

        Returns:
            Dict containing:
            - id: Flow ID
            - step: Current step
            - data: Flow data with validation context

        Note:
            Explicitly excludes member_id to maintain SINGLE SOURCE OF TRUTH
        """
        return {
            "id": self.id,
            "step": self.step,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], member_id: str) -> 'FlowState':
        """Create FlowState from dict and member_id

        Args:
            data: Dictionary containing flow state data
            member_id: Member ID from top level state

        Returns:
            FlowState instance

        Note:
            member_id must come from top level state to maintain SINGLE SOURCE OF TRUTH
        """
        return cls(
            id=data.get("id", ""),
            member_id=member_id,  # From top level - SINGLE SOURCE OF TRUTH
            step=data.get("step", 0),
            data=data.get("data", {
                "flow_type": None,
                "_validation_context": {},
                "_validation_state": {}
            })
        )

    @classmethod
    def create(cls, flow_id: str, member_id: str, flow_type: str) -> 'FlowState':
        """Create new FlowState with proper initialization

        Args:
            flow_id: Unique flow identifier
            member_id: Member ID from top level state
            flow_type: Type of flow

        Returns:
            FlowState instance

        Note:
            member_id must come from top level state to maintain SINGLE SOURCE OF TRUTH
        """
        return cls(
            id=flow_id,
            member_id=member_id,  # From top level - SINGLE SOURCE OF TRUTH
            step=0,
            data={
                "flow_type": flow_type,
                "_validation_context": {},
                "_validation_state": {}
            }
        )


class StepType(Enum):
    """Types of interaction steps"""
    TEXT = "text"
    BUTTON = "button"
    LIST = "list"


@dataclass
class Step:
    """Single interaction step"""
    id: str
    type: StepType
    message: Union[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[Any], Any]] = None

    def validate(self, input_data: Any) -> bool:
        """Validate step input"""
        try:
            # Special validation for confirmation
            if self.id == "confirm" and isinstance(input_data, dict):
                interactive = input_data.get("interactive", {})
                if (interactive.get("type") == "button_reply" and
                        interactive.get("button_reply", {}).get("id") == "confirm_action"):
                    return True
                return False

            # Use custom validator if provided
            if not self.validator:
                return True

            try:
                return self.validator(input_data)
            except Exception as validation_error:
                # Log validation error with context
                logger.error(
                    f"Validation failed in step {self.id}",
                    extra={
                        "step_id": self.id,
                        "validator": self.validator.__name__ if hasattr(self.validator, '__name__') else str(self.validator),
                        "input": input_data,
                        "error": str(validation_error)
                    },
                    exc_info=True
                )
                # Re-raise with context
                raise ValueError(f"Validation error in step {self.id}: {str(validation_error)}")

        except Exception as e:
            # Only log non-validation errors
            if not isinstance(e, ValueError):
                logger.error(f"Unexpected error in step {self.id}: {str(e)}")
            raise

    def transform(self, input_data: Any) -> Any:
        """Transform step input"""
        try:
            return self.transformer(input_data) if self.transformer else input_data
        except Exception as e:
            logger.error(f"Transform error in {self.id}: {str(e)}")
            raise ValueError(str(e))

    def get_message(self, state: Any) -> Dict[str, Any]:
        """Get step message"""
        try:
            # Ensure state is a dictionary
            if not isinstance(state, dict):
                state = {"data": state}
            return self.message(state) if callable(self.message) else self.message
        except Exception as e:
            logger.error(f"Message error in {self.id}: {str(e)}")
            raise ValueError(str(e))


class Flow:
    """Base class for all flows"""

    def __init__(self, id: str, steps: List[Step], state: Optional[FlowState] = None):
        """Initialize flow with proper state management

        Args:
            id: Flow identifier
            steps: List of flow steps
            state: Optional FlowState for initialization

        Note:
            If state is provided, it must contain member_id from top level state
        """
        self.id = id
        self.steps = steps
        self.current_index = 0
        self.data: Dict[str, Any] = {}
        self._previous_data: Dict[str, Any] = {}  # Store previous state for rollback
        self.state: Optional[FlowState] = None  # Current flow state

        # Initialize state if provided
        if state:
            self.set_state(state)

    @property
    def current_step(self) -> Optional[Step]:
        """Get current step"""
        return self.steps[self.current_index] if 0 <= self.current_index < len(self.steps) else None

    @property
    def member_id(self) -> Optional[str]:
        """Get member ID from current state"""
        return self.state.member_id if self.state else None

    def process_input(self, input_data: Any) -> Optional[Dict[str, Any]]:
        """Process input and return next message or None if complete"""
        if not self.state:
            raise ValueError("Flow state not initialized")

        step = self.current_step
        if not step:
            return None

        try:
            # Create new validation state
            validation_state = {
                "step_id": step.id,
                "step_index": self.current_index,
                "input": input_data,
                "timestamp": audit.get_current_timestamp()
            }

            # Create new state with validation info
            new_state = FlowState(
                id=self.id,
                member_id=self.state.member_id,
                step=self.current_index,
                data={
                    **self.state.data,
                    "_validation_state": validation_state
                }
            )

            # Log flow event at start of processing
            audit.log_flow_event(
                self.id,
                "step_start",
                step.id,
                new_state.to_dict(),
                "in_progress"
            )

            # Log input processing
            logger.debug(f"[Flow {self.id}] Processing input for step {step.id}")
            logger.debug(f"[Flow {self.id}] Input data: {input_data}")
            logger.debug(f"[Flow {self.id}] Current validation state: {validation_state}")

            # Validate input
            validation_result = step.validate(input_data)
            audit.log_validation_event(
                self.id,
                step.id,
                input_data,
                validation_result
            )

            if not validation_result:
                from services.whatsapp.types import WhatsAppMessage

                # Update validation state with error
                new_state.data["_validation_state"].update({
                    "success": False,
                    "error": "Invalid input"
                })

                # Log validation failure
                audit.log_flow_event(
                    self.id,
                    "validation_error",
                    step.id,
                    new_state.to_dict(),
                    "failure",
                    "Invalid input"
                )

                # Store error state
                self.set_state(new_state)

                channel_identifier = new_state.data.get("channel", {}).get("identifier")
                if step.id == "amount":
                    return WhatsAppMessage.create_text(
                        channel_identifier,
                        "Invalid amount format. Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1\n\n"
                        "Please ensure you enter a valid number with an optional currency code."
                    )
                return WhatsAppMessage.create_text(
                    channel_identifier,
                    "Invalid input"
                )

            # Transform input
            transformed_data = step.transform(input_data)

            # Create success state
            success_state = FlowState(
                id=self.id,
                member_id=self.state.member_id,
                step=self.current_index + 1,  # Move to next step
                data={
                    **new_state.data,
                    step.id if step.id != "amount" else "amount_denom": transformed_data,
                    "_validation_state": {
                        **validation_state,
                        "success": True,
                        "transformed": transformed_data
                    }
                }
            )

            # Log successful state transition
            audit.log_state_transition(
                self.id,
                new_state.to_dict(),
                success_state.to_dict(),
                "success"
            )

            # Update flow state
            self.set_state(success_state)

            # Complete or get next message
            next_message = (
                self.complete()
                if self.current_index >= len(self.steps)
                else self.current_step.get_message(self.state.data)
                if self.current_step
                else None
            )

            return next_message

        except ValueError as validation_error:
            # Handle validation errors with context
            from services.whatsapp.types import WhatsAppMessage

            # Create error state
            error_state = FlowState(
                id=self.id,
                member_id=self.state.member_id,
                step=self.current_index,
                data={
                    **self.state.data,
                    "_validation_state": {
                        **validation_state,
                        "success": False,
                        "error": str(validation_error)
                    }
                }
            )

            # Log validation error
            audit.log_flow_event(
                self.id,
                "validation_error",
                step.id,
                error_state.to_dict(),
                "failure",
                str(validation_error)
            )

            # Store error state
            self.set_state(error_state)

            channel_identifier = error_state.data.get("channel", {}).get("identifier")
            return WhatsAppMessage.create_text(
                channel_identifier,
                str(validation_error)
            )

        except Exception as e:
            error_msg = f"Process error in {step.id}: {str(e)}"
            logger.error(error_msg)

            # Log error event
            audit.log_flow_event(
                self.id,
                "process_error",
                step.id,
                self.state.to_dict(),
                "failure",
                error_msg
            )

            # Attempt smart state recovery
            current_step = self.current_step.id if self.current_step else None

            # First try to recover to current step
            last_valid_state = audit.get_last_valid_state(self.id, current_step)
            if last_valid_state:
                recovery_state = FlowState.from_dict(last_valid_state, self.state.member_id)
                self.set_state(recovery_state)
                logger.info(f"Recovered to valid state at step {current_step}")
                channel_identifier = recovery_state.data.get("channel", {}).get("identifier")
                return WhatsAppMessage.create_text(
                    channel_identifier,
                    "Recovered from error. Please try your last action again."
                )

            # If can't recover to current step, try to get recovery path
            if current_step:
                recovery_path = audit.get_recovery_path(self.id, current_step)
                if recovery_path:
                    # Find the last successful state in the path
                    for state_dict in reversed(recovery_path):
                        if state_dict.get("_validation_state", {}).get("success"):
                            recovery_state = FlowState.from_dict(state_dict, self.state.member_id)
                            self.set_state(recovery_state)
                            recovered_step = state_dict.get("_validation_state", {}).get("step_id", "previous")
                            logger.info(f"Recovered to earlier valid state at step {recovered_step}")
                            channel_identifier = recovery_state.data.get("channel", {}).get("identifier")
                            return WhatsAppMessage.create_text(
                                channel_identifier,
                                "Recovered to a previous step. Please continue from there."
                            )

            # If all recovery attempts fail, return error
            from services.whatsapp.types import WhatsAppMessage
            channel_identifier = self.state.data.get("channel", {}).get("identifier")
            return WhatsAppMessage.create_text(
                channel_identifier,
                f"Error: {str(e)}"
            )

    def complete(self) -> Optional[Dict[str, Any]]:
        """Handle flow completion - override in subclasses"""
        # Log flow completion
        audit.log_flow_event(
            self.id,
            "complete",
            None,
            self.data,
            "success"
        )
        return None

    def get_state(self) -> FlowState:
        """Get current flow state"""
        if not self.state:
            raise ValueError("Flow state not initialized")
        return self.state

    def set_state(self, state: Union[FlowState, Dict[str, Any]]) -> None:
        """Set flow state

        Args:
            state: Either a FlowState object or a dictionary to convert to FlowState
        """
        try:
            # Convert dict to FlowState if needed
            if isinstance(state, dict):
                if not self.member_id:
                    raise ValueError("Cannot convert dict to FlowState without member_id")
                state = FlowState.from_dict(state, self.member_id)
            elif not isinstance(state, FlowState):
                raise ValueError("State must be either FlowState or dict")

            # Log state change
            logger.debug(f"[Flow {self.id}] Setting flow state")
            logger.debug(f"[Flow {self.id}] Current step: {self.current_index}")
            logger.debug(f"[Flow {self.id}] New state: {state.to_dict()}")

            # Store old state for logging
            old_state = self.state.to_dict() if self.state else None

            # Update internal state
            self.state = state
            self.current_index = state.step
            self.data = state.data
            self._previous_data = self.data.copy()

            # Log state transition
            if old_state:
                audit.log_state_transition(
                    self.id,
                    old_state,
                    state.to_dict(),
                    "success"
                )

            # Log final state
            logger.debug(f"[Flow {self.id}] State update complete")
            logger.debug(f"[Flow {self.id}] - Member ID: {state.member_id}")
            logger.debug(f"[Flow {self.id}] - Step: {state.step}")
            logger.debug(f"[Flow {self.id}] - Data keys: {list(state.data.keys())}")

        except Exception as e:
            error_msg = f"Error setting flow state: {str(e)}"
            logger.error(error_msg)
            audit.log_flow_event(
                self.id,
                "set_state_error",
                None,
                state,
                "failure",
                error_msg
            )
            raise ValueError(error_msg)
