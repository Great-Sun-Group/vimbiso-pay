"""Clean flow management implementation"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


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

    def get_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get step message"""
        try:
            return self.message(state) if callable(self.message) else self.message
        except Exception as e:
            logger.error(f"Message error in {self.id}: {str(e)}")
            raise ValueError(str(e))


class Flow:
    """Base class for all flows"""

    def __init__(self, id: str, steps: List[Step]):
        self.id = id
        self.steps = steps
        self.current_index = 0
        self.data: Dict[str, Any] = {}
        self._previous_data: Dict[str, Any] = {}  # Store previous state for rollback

    @property
    def current_step(self) -> Optional[Step]:
        """Get current step"""
        return self.steps[self.current_index] if 0 <= self.current_index < len(self.steps) else None

    def process_input(self, input_data: Any) -> Optional[Dict[str, Any]]:
        """Process input and return next message or None if complete"""
        step = self.current_step
        if not step:
            return None

        # Store complete current state with validation context
        validation_state = {
            "_step": self.current_index,
            "_validation_state": {
                "step_id": step.id,
                "input": input_data,
                "timestamp": audit.get_current_timestamp()
            }
        }

        # Preserve existing validation context while adding new state
        self._previous_data = {
            **self.data,
            **validation_state,
            "_previous_validation": self.data.get("_validation_state", {})
        }

        # Log flow event at start of processing
        audit.log_flow_event(
            self.id,
            "step_start",
            step.id,
            self._previous_data,
            "in_progress"
        )

        # Validate and transform input
        try:
            validation_result = step.validate(input_data)
            audit.log_validation_event(
                self.id,
                step.id,
                input_data,
                validation_result
            )

            if not validation_result:
                from services.whatsapp.types import WhatsAppMessage
                # Restore previous state while preserving ALL context
                self.data = self._previous_data.copy()
                self.data["_validation_error"] = True

                # Log validation failure
                audit.log_flow_event(
                    self.id,
                    "validation_error",
                    step.id,
                    self.data,
                    "failure",
                    "Invalid input"
                )

                if step.id == "amount":
                    return WhatsAppMessage.create_text(
                        self.data.get("mobile_number", ""),
                        "Invalid amount format. Examples:\n"
                        "100     (USD)\n"
                        "USD 100\n"
                        "ZWG 100\n"
                        "XAU 1\n\n"
                        "Please ensure you enter a valid number with an optional currency code."
                    )
                return WhatsAppMessage.create_text(
                    self.data.get("mobile_number", ""),
                    "Invalid input"
                )

        except ValueError as validation_error:
            # Handle validation errors with context
            from services.whatsapp.types import WhatsAppMessage

            # Restore previous state
            self.data = self._previous_data.copy()
            self.data["_validation_error"] = True

            # Log validation error
            audit.log_flow_event(
                self.id,
                "validation_error",
                step.id,
                self.data,
                "failure",
                str(validation_error)
            )

            return WhatsAppMessage.create_text(
                self.data.get("mobile_number", ""),
                str(validation_error)
            )

        try:
            # Update flow data
            transformed_data = step.transform(input_data)

            # Store transformed data under step ID to preserve structure
            if step.id == "amount":
                # Store amount data under amount_denom key to better reflect its structure
                self.data["amount_denom"] = transformed_data
            else:
                self.data[step.id] = transformed_data

            # Move to next step only after successful transformation
            self.current_index += 1

            # Store validation context
            validation_context = {
                "_validation_success": True,
                "_validation_state": {
                    "step_id": step.id,
                    "input": input_data,
                    "transformed": transformed_data,
                    "timestamp": audit.get_current_timestamp()
                }
            }

            # Update flow data preserving context
            self.data.update(validation_context)
            self._previous_data.update(validation_context)

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

            # Attempt recovery from last valid state
            last_valid_state = audit.get_last_valid_state(self.id)
            if last_valid_state:
                self.data = last_valid_state
                logger.info(f"Recovered to last valid state for flow {self.id}")
            else:
                # Fallback to previous state if recovery fails
                self.data = self._previous_data

            from services.whatsapp.types import WhatsAppMessage
            return WhatsAppMessage.create_text(
                self.data.get("mobile_number", ""),
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
        state = {
            "id": self.id,
            "step": self.current_index,
            "data": self.data,
            "_previous_data": self._previous_data  # Include previous state
        }
        # Log state retrieval
        audit.log_flow_event(
            self.id,
            "get_state",
            None,
            state,
            "success"
        )
        return state

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set flow state while preserving existing data"""
        if isinstance(state, dict):
            # Log current state before changes
            logger.debug(f"[Flow {self.id}] Setting flow state")
            logger.debug(f"[Flow {self.id}] Current data: {self.data}")
            logger.debug(f"[Flow {self.id}] Current step: {self.current_index}")
            logger.debug(f"[Flow {self.id}] New state to merge: {state}")

            old_state = self.get_state()

            # Merge new data with existing data
            if "data" in state:
                logger.debug(f"[Flow {self.id}] Merging data fields:")
                logger.debug(f"[Flow {self.id}] - Existing data fields: {list(self.data.keys())}")
                logger.debug(f"[Flow {self.id}] - New data fields: {list(state['data'].keys())}")

                # Preserve validation context during merge
                validation_context = {k: v for k, v in self.data.items() if k.startswith('_')}

                self.data = {
                    **validation_context,  # Keep validation context
                    **self.data,  # Keep existing data
                    **state.get("data", {})  # Merge new data
                }

                # Restore previous data if available
                if "_previous_data" in state:
                    self._previous_data = state["_previous_data"]

                logger.debug(f"[Flow {self.id}] - Merged data fields: {list(self.data.keys())}")
                logger.debug(f"[Flow {self.id}] - Full merged data: {self.data}")

            # Update step index
            old_step = self.current_index
            self.current_index = state.get("step", 0)
            logger.debug(f"[Flow {self.id}] Step transition: {old_step} -> {self.current_index}")

            # Log state transition
            audit.log_state_transition(
                self.id,
                old_state,
                self.get_state(),
                "success"
            )

            # Log final state summary
            logger.debug(f"[Flow {self.id}] State update complete")
            logger.debug(f"[Flow {self.id}] - Final step: {self.current_index}")
            logger.debug(f"[Flow {self.id}] - Final data keys: {list(self.data.keys())}")
            logger.debug(f"[Flow {self.id}] - Final data values: {self.data}")
