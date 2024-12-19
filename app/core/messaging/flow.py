"""Clean flow management implementation"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union

import logging

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
    message: Union[str, Callable[[Dict[str, Any]], str]]
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[Any], Any]] = None

    def validate(self, input_data: Any) -> bool:
        """Validate step input"""
        try:
            return self.validator(input_data) if self.validator else True
        except Exception as e:
            logger.error(f"Validation error in {self.id}: {str(e)}")
            return False

    def transform(self, input_data: Any) -> Any:
        """Transform step input"""
        try:
            return self.transformer(input_data) if self.transformer else input_data
        except Exception as e:
            logger.error(f"Transform error in {self.id}: {str(e)}")
            raise ValueError(str(e))

    def get_message(self, state: Dict[str, Any]) -> str:
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

    @property
    def current_step(self) -> Optional[Step]:
        """Get current step"""
        return self.steps[self.current_index] if 0 <= self.current_index < len(self.steps) else None

    def process_input(self, input_data: Any) -> Optional[str]:
        """Process input and return next message or None if complete"""
        step = self.current_step
        if not step:
            return None

        # Validate and transform input
        if not step.validate(input_data):
            return "Invalid input"

        try:
            # Update flow data
            self.data[step.id] = step.transform(input_data)

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
            return f"Error: {str(e)}"

    def complete(self) -> Optional[str]:
        """Handle flow completion - override in subclasses"""
        return None

    def get_state(self) -> Dict[str, Any]:
        """Get flow state"""
        return {
            "id": self.id,
            "step": self.current_index,
            "data": self.data
        }

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set flow state"""
        if isinstance(state, dict):
            self.data = state.get("data", {})
            self.current_index = state.get("step", 0)
