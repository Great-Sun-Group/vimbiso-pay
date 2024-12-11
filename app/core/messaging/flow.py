"""Flow management implementation for progressive WhatsApp interactions"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union

from services.state.service import StateStage
from .types import Message as WhatsAppMessage


class StepType(Enum):
    """Types of interaction steps supported"""
    TEXT_INPUT = 'text_input'          # Free text input
    LIST_SELECT = 'list_select'        # List of options
    BUTTON_SELECT = 'button_select'    # Quick reply buttons


@dataclass
class Step:
    """Represents a single interaction step"""
    id: str
    type: StepType
    stage: str  # Maps to StateStage
    message: Union[WhatsAppMessage, Callable[[Dict[str, Any]], WhatsAppMessage]]
    validation: Optional[Callable[[Any], bool]] = None
    transform: Optional[Callable[[Any], Any]] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None

    def validate(self, input_value: Any) -> bool:
        """Validate step input"""
        if self.validation:
            return self.validation(input_value)
        return True

    def transform_input(self, input_value: Any) -> Any:
        """Transform step input"""
        if self.transform:
            return self.transform(input_value)
        return input_value

    def should_execute(self, state: Dict[str, Any]) -> bool:
        """Check if step should be executed based on condition"""
        if self.condition:
            return self.condition(state)
        return True


class Flow:
    """Manages progressive interaction flow"""
    def __init__(self, id: str, steps: List[Step]):
        self.id = id
        self.steps = steps
        self.current_step_index = 0
        self._state: Dict[str, Any] = {}
        self._initial_state: Dict[str, Any] = {}

    def _get_clean_state(self) -> Dict[str, Any]:
        """Get a clean state with essential fields"""
        clean_state = {}

        # Always preserve these basic fields if they exist
        preserve_fields = {
            "phone",
            "authorizer_member_id",
            "issuer_member_id",
            "sender_account",
            "sender_account_id",
            "jwt_token"
        }

        # Add step IDs to preserved fields
        for step in self.steps:
            preserve_fields.add(step.id)

        # Preserve all essential fields
        for field in preserve_fields:
            if field in self._state:
                clean_state[field] = self._state[field]

        return clean_state

    @property
    def current_step(self) -> Optional[Step]:
        """Get current step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def state(self) -> Dict[str, Any]:
        """Get flow state"""
        return self._state

    @state.setter
    def state(self, value: Dict[str, Any]) -> None:
        """Set flow state"""
        if not self._initial_state:
            # Store initial state first time state is set
            self._initial_state = self._get_clean_state()

        # Start with a clean state
        clean_state = self._get_clean_state()

        # Update with new values, preserving step data
        for key, val in value.items():
            # Always preserve step data
            if key in {step.id for step in self.steps}:
                clean_state[key] = val
            # For other fields, don't overwrite preserved fields
            elif key not in clean_state:
                clean_state[key] = val

        self._state = clean_state

    def update_state(self, step_id: str, value: Any) -> None:
        """Update state for a specific step"""
        # Get clean state but preserve all step data
        clean_state = self._get_clean_state()

        # Update the specific step's data
        clean_state[step_id] = value

        # Set the new state
        self._state = clean_state

    def next(self) -> Optional[Step]:
        """Move to next applicable step"""
        while self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            if self.current_step.should_execute(self._state):
                return self.current_step
        return None

    def back(self) -> Optional[Step]:
        """Move to previous applicable step"""
        while self.current_step_index > 0:
            self.current_step_index -= 1
            if self.current_step.should_execute(self._state):
                return self.current_step
        return None

    def to_state_data(self) -> Dict[str, Any]:
        """Convert flow data to state format"""
        return {
            "stage": self.current_step.stage if self.current_step else StateStage.INIT.value,
            "option": f"flow_{self.id}",
            "flow_data": {
                "id": self.id,
                "current_step": self.current_step_index,
                "data": self._state
            }
        }

    @classmethod
    def from_state_data(cls, state_data: Dict[str, Any]) -> Optional['Flow']:
        """Reconstruct flow from state data"""
        flow_data = state_data.get("flow_data", {})
        if not flow_data:
            return None

        flow_id = flow_data.get("id")
        if not flow_id:
            return None

        # Flow instances should be registered/cached
        flow = cls.get_flow_by_id(flow_id)
        if flow:
            flow.current_step_index = flow_data.get("current_step", 0)
            flow._state = flow_data.get("data", {})
            return flow
        return None

    @staticmethod
    def get_flow_by_id(flow_id: str) -> Optional['Flow']:
        """Get flow instance by ID - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_flow_by_id")
