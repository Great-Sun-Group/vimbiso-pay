"""Flow management implementation for progressive WhatsApp interactions"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import logging
import json
import time

from services.state.service import StateStage
from services.state.exceptions import InvalidStateError
from .types import Message as WhatsAppMessage

logger = logging.getLogger(__name__)


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
        """Validate step input with error handling"""
        try:
            if self.validation:
                return self.validation(input_value)
            return True
        except Exception as e:
            logger.error(f"Step validation error for {self.id}: {str(e)}")
            return False

    def transform_input(self, input_value: Any) -> Any:
        """Transform step input with error handling"""
        try:
            if self.transform:
                return self.transform(input_value)
            return input_value
        except Exception as e:
            logger.error(f"Step transform error for {self.id}: {str(e)}")
            raise ValueError(f"Failed to transform input: {str(e)}")

    def should_execute(self, state: Dict[str, Any]) -> bool:
        """Check if step should be executed based on condition"""
        try:
            if self.condition:
                return self.condition(state)
            return True
        except Exception as e:
            logger.error(f"Step condition error for {self.id}: {str(e)}")
            return False


class Flow:
    """Manages progressive interaction flow with enhanced state management"""
    def __init__(self, id: str, steps: List[Step]):
        self.id = id
        self.steps = steps
        self.current_step_index = 0
        self._state: Dict[str, Any] = {}
        self._initial_state: Dict[str, Any] = {}
        self._version = 1  # Add version tracking

    def _validate_state_data(self, state_data: Dict[str, Any]) -> None:
        """Validate state data structure and required fields"""
        if not isinstance(state_data, dict):
            raise InvalidStateError("State must be a dictionary")

        # Validate essential fields
        required_fields = {"phone"}
        missing_fields = required_fields - set(state_data.keys())
        if missing_fields:
            raise InvalidStateError(f"State missing required fields: {missing_fields}")

        # Validate step data
        for step in self.steps:
            if step.id in state_data:
                try:
                    # Attempt to validate step data
                    if not step.validate(state_data[step.id]):
                        raise InvalidStateError(f"Invalid data for step {step.id}")
                except Exception as e:
                    logger.error(f"Step data validation error: {str(e)}")
                    raise InvalidStateError(f"Step data validation failed: {str(e)}")

    def _preserve_nested_state(self, current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve nested state data with validation"""
        preserved = {}

        # Preserve step data
        step_ids = {step.id for step in self.steps}
        for key in step_ids:
            if key in current:
                preserved[key] = current[key]
            if key in new:
                preserved[key] = new[key]

        # Preserve essential data
        essential_fields = {
            "phone",
            "profile",
            "current_account",
            "authorizer_member_id",
            "issuer_member_id",
            "sender_account",
            "sender_account_id",
            "jwt_token"
        }
        for field in essential_fields:
            if field in current:
                preserved[field] = current[field]
            if field in new:
                preserved[field] = new[field]

        # Add version tracking
        preserved["version"] = self._version + 1
        preserved["last_updated"] = time.time()

        return preserved

    def _backup_state(self) -> None:
        """Create state backup"""
        try:
            self._backup = json.dumps(self._state)
        except Exception as e:
            logger.error(f"State backup failed: {str(e)}")

    def _restore_state(self) -> bool:
        """Restore state from backup"""
        try:
            if hasattr(self, '_backup'):
                self._state = json.loads(self._backup)
                return True
        except Exception as e:
            logger.error(f"State restore failed: {str(e)}")
        return False

    @property
    def current_step(self) -> Optional[Step]:
        """Get current step with validation"""
        if not 0 <= self.current_step_index < len(self.steps):
            logger.error(f"Invalid step index: {self.current_step_index}")
            return None
        return self.steps[self.current_step_index]

    @property
    def state(self) -> Dict[str, Any]:
        """Get flow state"""
        return self._state

    @state.setter
    def state(self, value: Dict[str, Any]) -> None:
        """Set flow state with validation and preservation"""
        try:
            # Validate new state
            self._validate_state_data(value)

            if not self._initial_state:
                # Store initial state first time
                self._initial_state = self._preserve_nested_state({}, value)

            # Create backup before update
            self._backup_state()

            # Update state with preservation
            self._state = self._preserve_nested_state(self._state, value)
            self._version += 1

        except Exception as e:
            logger.error(f"State update failed: {str(e)}")
            if not self._restore_state():
                # If restore fails, reset to initial state
                self._state = self._initial_state.copy()
            raise

    def update_state(self, step_id: str, value: Any) -> None:
        """Update state for a specific step with validation"""
        try:
            # Validate step exists
            if step_id not in {step.id for step in self.steps}:
                raise InvalidStateError(f"Invalid step ID: {step_id}")

            # Create backup
            self._backup_state()

            # Get clean state but preserve all step data
            clean_state = self._preserve_nested_state(self._state, {})
            clean_state[step_id] = value

            # Validate and update
            self._validate_state_data(clean_state)
            self._state = clean_state
            self._version += 1

        except Exception as e:
            logger.error(f"Step state update failed: {str(e)}")
            if not self._restore_state():
                self._state = self._initial_state.copy()
            raise

    def next(self) -> Optional[Step]:
        """Move to next applicable step with validation"""
        try:
            original_index = self.current_step_index
            while self.current_step_index < len(self.steps) - 1:
                self.current_step_index += 1
                if self.current_step and self.current_step.should_execute(self._state):
                    return self.current_step
            return None
        except Exception as e:
            logger.error(f"Step progression failed: {str(e)}")
            self.current_step_index = original_index
            return None

    def back(self) -> Optional[Step]:
        """Move to previous applicable step with validation"""
        try:
            original_index = self.current_step_index
            while self.current_step_index > 0:
                self.current_step_index -= 1
                if self.current_step and self.current_step.should_execute(self._state):
                    return self.current_step
            return None
        except Exception as e:
            logger.error(f"Step regression failed: {str(e)}")
            self.current_step_index = original_index
            return None

    def to_state_data(self) -> Dict[str, Any]:
        """Convert flow data to state format with validation"""
        try:
            return {
                "stage": self.current_step.stage if self.current_step else StateStage.INIT.value,
                "option": f"flow_{self.id}",
                "flow_data": {
                    "id": self.id,
                    "current_step": self.current_step_index,
                    "data": self._state,
                    "version": self._version
                }
            }
        except Exception as e:
            logger.error(f"State data conversion failed: {str(e)}")
            raise

    def validate_state(self) -> bool:
        """Validate current flow state"""
        try:
            # Validate basic structure
            self._validate_state_data(self._state)

            # Validate step index
            if not 0 <= self.current_step_index < len(self.steps):
                return False

            # Validate current step
            current = self.current_step
            if not current:
                return False

            # Validate step execution
            if not current.should_execute(self._state):
                return False

            return True
        except Exception:
            return False

    def recover_state(self) -> bool:
        """Attempt to recover corrupted state"""
        try:
            # Try to restore from backup
            if self._restore_state():
                if self.validate_state():
                    return True

            # Fall back to initial state
            if self._initial_state:
                self._state = self._initial_state.copy()
                self.current_step_index = 0
                return self.validate_state()

            return False
        except Exception as e:
            logger.error(f"State recovery failed: {str(e)}")
            return False

    @classmethod
    def from_state_data(cls, state_data: Dict[str, Any]) -> Optional['Flow']:
        """Reconstruct flow from state data with validation"""
        try:
            flow_data = state_data.get("flow_data", {})
            if not flow_data:
                return None

            flow_id = flow_data.get("id")
            if not flow_id:
                return None

            # Get flow instance
            flow = cls.get_flow_by_id(flow_id)
            if not flow:
                return None

            # Restore state
            flow.current_step_index = flow_data.get("current_step", 0)
            flow._state = flow_data.get("data", {})
            flow._version = flow_data.get("version", 1)

            # Validate restored state
            if not flow.validate_state():
                if not flow.recover_state():
                    return None

            return flow

        except Exception as e:
            logger.error(f"Flow reconstruction failed: {str(e)}")
            return None

    @staticmethod
    def get_flow_by_id(flow_id: str) -> Optional['Flow']:
        """Get flow instance by ID - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_flow_by_id")
