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

        # Initialize state if provided
        if state:
            self.set_state(state.to_dict())

    @property
    def current_step(self) -> Optional[Step]:
        """Get current step"""
        return self.steps[self.current_index] if 0 <= self.current_index < len(self.steps) else None

    def process_input(self, input_data: Any) -> Optional[Dict[str, Any]]:
        """Process input and return next message or None if complete"""
        step = self.current_step
        if not step:
            return None

        try:
            # Initialize validation state in data
            self.data["_validation_state"] = {
                "step_id": step.id,
                "step_index": self.current_index,
                "input": input_data,
                "timestamp": audit.get_current_timestamp()
            }

            # Store previous state
            self._previous_data = self.data.copy()

            # Log flow event at start of processing
            audit.log_flow_event(
                self.id,
                "step_start",
                step.id,
                self._previous_data,
                "in_progress"
            )

            # Log input processing
            logger.debug(f"[Flow {self.id}] Processing input for step {step.id}")
            logger.debug(f"[Flow {self.id}] Input data: {input_data}")
            logger.debug(f"[Flow {self.id}] Current validation state: {self.data['_validation_state']}")

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
                # Restore previous state and mark validation error
                self.data = self._previous_data.copy()
                self.data["_validation_state"].update({
                    "success": False,
                    "error": "Invalid input"
                })

                # Log validation failure
                audit.log_flow_event(
                    self.id,
                    "validation_error",
                    step.id,
                    self.data,
                    "failure",
                    "Invalid input"
                )

                channel_identifier = self.data.get("channel", {}).get("identifier")
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

            # Store transformed data under step ID to preserve structure
            if step.id == "amount":
                # Store amount data under amount_denom key to better reflect its structure
                self.data["amount_denom"] = transformed_data
            else:
                self.data[step.id] = transformed_data

            # Move to next step only after successful transformation
            self.current_index += 1

            # Update validation state with success and transformed data
            self.data["_validation_state"].update({
                "success": True,
                "transformed": transformed_data
            })

            # Store in previous data
            self._previous_data = self.data.copy()

            # Log successful state transition
            audit.log_state_transition(
                self.id,
                self._previous_data,
                self.data,
                "success"
            )

            # Complete or get next message
            next_message = (
                self.complete()
                if self.current_index >= len(self.steps)
                else self.current_step.get_message(self.data)
                if self.current_step
                else None
            )

            return next_message

        except ValueError as validation_error:
            # Handle validation errors with context
            from services.whatsapp.types import WhatsAppMessage

            # Restore previous state and mark validation error
            self.data = self._previous_data.copy()
            self.data["_validation_state"].update({
                "success": False,
                "error": str(validation_error)
            })

            # Log validation error
            audit.log_flow_event(
                self.id,
                "validation_error",
                step.id,
                self.data,
                "failure",
                str(validation_error)
            )

            channel_identifier = self.data.get("channel", {}).get("identifier")
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
                self._previous_data,
                "failure",
                error_msg
            )

            # Attempt smart state recovery
            current_step = self.current_step.id if self.current_step else None

            # First try to recover to current step
            last_valid_state = audit.get_last_valid_state(self.id, current_step)
            if last_valid_state:
                self.data = last_valid_state
                logger.info(f"Recovered to valid state at step {current_step}")
                channel_identifier = self.data.get("channel", {}).get("identifier")
                return WhatsAppMessage.create_text(
                    channel_identifier,
                    "Recovered from error. Please try your last action again."
                )

            # If can't recover to current step, try to get recovery path
            if current_step:
                recovery_path = audit.get_recovery_path(self.id, current_step)
                if recovery_path:
                    # Find the last successful state in the path
                    for state in reversed(recovery_path):
                        if state.get("_validation_state", {}).get("success"):
                            self.data = state
                            recovered_step = state.get("_validation_state", {}).get("step_id", "previous")
                            logger.info(f"Recovered to earlier valid state at step {recovered_step}")
                            channel_identifier = self.data.get("channel", {}).get("identifier")
                            return WhatsAppMessage.create_text(
                                channel_identifier,
                                "Recovered to a previous step. Please continue from there."
                            )

            # If all recovery attempts fail, fallback to previous state
            logger.warning("Recovery failed, falling back to previous state")
            self.data = self._previous_data

            from services.whatsapp.types import WhatsAppMessage
            channel_identifier = self.data.get("channel", {}).get("identifier")
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

    def get_state(self) -> Dict[str, Any]:
        """Get flow state"""
        try:
            # Ensure data is a dictionary
            if not isinstance(self.data, dict):
                self.data = {}

            # Ensure required fields exist
            if "flow_type" not in self.data:
                self.data["flow_type"] = self.id.split("_")[0] if "_" in self.id else "unknown"

            # Ensure validation context exists in data
            if "_validation_context" not in self.data:
                self.data["_validation_context"] = {}
            if "_validation_state" not in self.data:
                self.data["_validation_state"] = {}

            # Build state with validation context only in data
            state = {
                "id": self.id,
                "step": self.current_index,
                "data": self.data,
                "_previous_data": self._previous_data
            }

            # Log state retrieval
            logger.debug(f"[Flow {self.id}] Getting state:")
            logger.debug(f"[Flow {self.id}] - Step: {self.current_index}")
            logger.debug(f"[Flow {self.id}] - Data keys: {list(self.data.keys())}")
            logger.debug(f"[Flow {self.id}] - Validation context: {self.data.get('_validation_context', {})}")

            audit.log_flow_event(
                self.id,
                "get_state",
                None,
                state,
                "success"
            )

            return state

        except Exception as e:
            error_msg = f"Error getting flow state: {str(e)}"
            logger.error(error_msg)
            audit.log_flow_event(
                self.id,
                "get_state_error",
                None,
                self.data,
                "failure",
                error_msg
            )
            raise ValueError(error_msg)

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set flow state while preserving existing data"""
        try:
            if not isinstance(state, dict):
                raise ValueError("State must be a dictionary")

            # Log current state before changes
            logger.debug(f"[Flow {self.id}] Setting flow state")
            logger.debug(f"[Flow {self.id}] Current data: {self.data}")
            logger.debug(f"[Flow {self.id}] Current step: {self.current_index}")
            logger.debug(f"[Flow {self.id}] New state to merge: {state}")

            old_state = self.get_state()

            # Merge data preserving validation context
            if "data" in state:
                new_data = state["data"]
                if not isinstance(new_data, dict):
                    raise ValueError("State data must be a dictionary")

                # Preserve validation context from new data
                validation_context = {
                    k: v for k, v in new_data.items()
                    if k in ("_validation_context", "_validation_state")
                }

                # Merge data with validation context preserved
                self.data = {
                    **self.data,  # Base data
                    **new_data,   # New data
                    **validation_context  # Ensure validation context from new data
                }

                # Update previous data
                self._previous_data = state.get("_previous_data", self.data.copy())

            # Update step index
            old_step = self.current_index
            self.current_index = state.get("step", 0)

            # Log state transition
            audit.log_state_transition(
                self.id,
                old_state,
                self.get_state(),
                "success"
            )

            # Log final state
            logger.debug(f"[Flow {self.id}] State update complete")
            logger.debug(f"[Flow {self.id}] - Step transition: {old_step} -> {self.current_index}")
            logger.debug(f"[Flow {self.id}] - Final data keys: {list(self.data.keys())}")
            logger.debug(f"[Flow {self.id}] - Validation context: {validation_context}")

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
