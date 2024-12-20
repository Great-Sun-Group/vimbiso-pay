"""Clean flow management implementation"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


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
            # Special validation for amount step
            if self.id == "amount":
                if isinstance(input_data, str):
                    # Handle currency prefix
                    parts = input_data.strip().split()
                    amount = parts[-1] if len(parts) > 1 else parts[0]
                    try:
                        # Log the validation attempt
                        logger.debug(f"Validating amount: {amount}")
                        float(amount.replace(',', ''))  # Handle comma-formatted numbers
                        return True
                    except ValueError as e:
                        logger.debug(f"Amount validation failed: {str(e)}")
                        return False
                elif isinstance(input_data, (int, float)):
                    return True
                return False

            # Special validation for confirmation
            if self.id == "confirm" and isinstance(input_data, dict):
                interactive = input_data.get("interactive", {})
                if (interactive.get("type") == "button_reply" and
                        interactive.get("button_reply", {}).get("id") == "confirm_action"):
                    return True
                return False

            # Use custom validator if provided
            return self.validator(input_data) if self.validator else True
        except Exception as e:
            logger.error(f"Validation error in {self.id}: {str(e)}")
            return False

    def transform(self, input_data: Any) -> Any:
        """Transform step input"""
        try:
            # Special transformation for amount
            if self.id == "amount" and isinstance(input_data, str):
                parts = input_data.strip().split()
                amount = parts[-1].replace(',', '')  # Handle comma-formatted numbers
                denomination = parts[0] if len(parts) > 1 else "USD"
                # Log the transformation
                logger.debug(f"Transforming amount: {amount} {denomination}")
                return {
                    "amount": float(amount),
                    "denomination": denomination
                }

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

        # Store current state before modification
        self._previous_data = self.data.copy()

        # Validate and transform input
        if not step.validate(input_data):
            from services.whatsapp.types import WhatsAppMessage
            # Restore previous state on validation failure
            self.data = self._previous_data
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

        try:
            # Update flow data
            transformed_data = step.transform(input_data)
            # Store transformed data under step ID to preserve structure
            if step.id == "amount":
                # Store amount data under amount_denom key to better reflect its structure
                self.data["amount_denom"] = transformed_data
            else:
                self.data[step.id] = transformed_data

            # Move to next step
            self.current_index += 1

            # Complete or get next message
            return (
                self.complete()
                if self.current_index >= len(self.steps)
                else self.current_step.get_message(self.data)
                if self.current_step
                else None
            )

        except Exception as e:
            logger.error(f"Process error in {step.id}: {str(e)}")
            # Restore previous state on error
            self.data = self._previous_data
            from services.whatsapp.types import WhatsAppMessage
            return WhatsAppMessage.create_text(
                self.data.get("mobile_number", ""),
                f"Error: {str(e)}"
            )

    def complete(self) -> Optional[Dict[str, Any]]:
        """Handle flow completion - override in subclasses"""
        return None

    def get_state(self) -> Dict[str, Any]:
        """Get flow state"""
        return {
            "id": self.id,
            "step": self.current_index,
            "data": self.data,
            "_previous_data": self._previous_data  # Include previous state
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set flow state while preserving existing data"""
        if isinstance(state, dict):
            # Log current state before changes
            logger.debug(f"[Flow {self.id}] Setting flow state")
            logger.debug(f"[Flow {self.id}] Current data: {self.data}")
            logger.debug(f"[Flow {self.id}] Current step: {self.current_index}")
            logger.debug(f"[Flow {self.id}] New state to merge: {state}")

            # Merge new data with existing data
            if "data" in state:
                logger.debug(f"[Flow {self.id}] Merging data fields:")
                logger.debug(f"[Flow {self.id}] - Existing data fields: {list(self.data.keys())}")
                logger.debug(f"[Flow {self.id}] - New data fields: {list(state['data'].keys())}")

                self.data = {
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

            # Log final state summary
            logger.debug(f"[Flow {self.id}] State update complete")
            logger.debug(f"[Flow {self.id}] - Final step: {self.current_index}")
            logger.debug(f"[Flow {self.id}] - Final data keys: {list(self.data.keys())}")
            logger.debug(f"[Flow {self.id}] - Final data values: {self.data}")
