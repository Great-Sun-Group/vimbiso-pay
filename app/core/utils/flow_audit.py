"""Flow-specific audit logging"""
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
    """Handles flow-specific audit logging"""

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
        Log a flow event

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
        Log state transitions for audit

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
        Retrieve flow history for debugging

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
