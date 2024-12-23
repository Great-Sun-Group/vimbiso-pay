"""Flow-specific audit logging and recovery mechanisms"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configure the logger
logger = logging.getLogger("flow_audit")
logger.setLevel(logging.INFO)

# Create a file handler
handler = logging.FileHandler("flow_audit.log")
handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)


class FlowAuditLogger:
    """Handles flow-specific audit logging and recovery"""

    @staticmethod
    def get_current_timestamp() -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()

    @staticmethod
    def log_flow_event(
        flow_id: str,
        event_type: str,
        step_id: Optional[str],
        state: Dict[str, Any],
        status: str,
        error: Optional[str] = None
    ):
        """
        Log a flow event with complete state information

        :param flow_id: Unique identifier for the flow
        :param event_type: Type of event (start, step, complete, error)
        :param step_id: Current step ID if applicable
        :param state: Current flow state
        :param status: Status of the event (success, failure, interrupted)
        :param error: Error message if applicable
        """
        event_data = {
            "timestamp": FlowAuditLogger.get_current_timestamp(),
            "flow_id": flow_id,
            "event_type": event_type,
            "step_id": step_id,
            "state": state,
            "status": status
        }

        if error:
            event_data["error"] = error

        message = json.dumps(event_data)
        logger.info(message)

    @staticmethod
    def log_state_transition(
        flow_id: str,
        from_state: Dict[str, Any],
        to_state: Dict[str, Any],
        status: str,
        error: Optional[str] = None
    ):
        """
        Log state transitions for audit and recovery

        :param flow_id: Unique identifier for the flow
        :param from_state: Previous state
        :param to_state: New state
        :param status: Status of transition (success, failure)
        :param error: Error message if applicable
        """
        transition_data = {
            "timestamp": FlowAuditLogger.get_current_timestamp(),
            "flow_id": flow_id,
            "from_state": from_state,
            "to_state": to_state,
            "status": status
        }

        if error:
            transition_data["error"] = error

        message = json.dumps(transition_data)
        logger.info(message)

    @staticmethod
    def log_validation_event(
        flow_id: str,
        step_id: str,
        input_data: Any,
        validation_result: bool,
        error: Optional[str] = None
    ):
        """
        Log validation events for debugging

        :param flow_id: Unique identifier for the flow
        :param step_id: Current step ID
        :param input_data: Input that was validated
        :param validation_result: Result of validation
        :param error: Validation error message if applicable
        """
        validation_data = {
            "timestamp": FlowAuditLogger.get_current_timestamp(),
            "flow_id": flow_id,
            "step_id": step_id,
            "input": input_data,
            "result": validation_result
        }

        if error:
            validation_data["error"] = error

        message = json.dumps(validation_data)
        logger.info(message)

    @staticmethod
    def get_flow_history(flow_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve flow history for debugging and recovery

        :param flow_id: Flow ID to retrieve history for
        :return: List of flow events
        """
        history = []
        try:
            with open("flow_audit.log", "r") as f:
                for line in f:
                    try:
                        event = json.loads(line.split(" - ")[-1])
                        if event.get("flow_id") == flow_id:
                            history.append(event)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return history

    @staticmethod
    def get_last_valid_state(flow_id: str, current_step: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve last valid state for recovery with smart fallback and SINGLE SOURCE OF TRUTH enforcement

        :param flow_id: Flow ID to retrieve state for
        :param current_step: Current step ID for context-aware recovery
        :return: Last valid state if found
        """
        from .state_validator import StateValidator
        history = FlowAuditLogger.get_flow_history(flow_id)

        # First try to find last valid state at current step
        if current_step:
            for event in reversed(history):
                state = event.get("state", {})
                validation_state = state.get("_validation_state", {})

                if (event.get("status") == "success" and
                        validation_state.get("step_id") == current_step and
                        validation_state.get("success") is True):
                    # Validate and enforce SINGLE SOURCE OF TRUTH
                    validation_result = StateValidator.validate_state(state)
                    if validation_result.is_valid:
                        return state

        # If no valid state at current step, try to find last valid state at previous step
        current_step_found = False
        for event in reversed(history):
            state = event.get("state", {})
            validation_state = state.get("_validation_state", {})
            step_id = validation_state.get("step_id")

            # Mark when we find current step in history
            if step_id == current_step:
                current_step_found = True
                continue

            # Look for last valid state before current step
            if (current_step_found and
                    event.get("status") == "success" and
                    validation_state.get("success") is True):
                return state

        # If no valid states found, try to find initialization state
        for event in reversed(history):
            if event.get("event_type") == "initialization":
                state = event.get("state")
                if state:
                    # Validate and enforce SINGLE SOURCE OF TRUTH
                    validation_result = StateValidator.validate_state(state)
                    if validation_result.is_valid:
                        return state

        return None

    @staticmethod
    def get_recovery_path(flow_id: str, target_step: str) -> List[Dict[str, Any]]:
        """
        Get sequence of states needed to recover to target step

        :param flow_id: Flow ID to analyze
        :param target_step: Target step to recover to
        :return: List of states in sequence needed for recovery
        """
        history = FlowAuditLogger.get_flow_history(flow_id)
        recovery_path = []
        seen_steps = set()

        # Work backwards from target step
        for event in reversed(history):
            state = event.get("state", {})
            validation_state = state.get("_validation_state", {})
            step_id = validation_state.get("step_id")

            # Skip invalid states
            if not (event.get("status") == "success" and
                    validation_state.get("success") is True):
                continue

            # Add state if we haven't seen this step
            if step_id and step_id not in seen_steps:
                recovery_path.insert(0, state)
                seen_steps.add(step_id)

            # Stop if we've found a complete path
            if len(recovery_path) > 0 and recovery_path[0].get("_validation_state", {}).get("step_id") == target_step:
                break

        return recovery_path
