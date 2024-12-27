"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger
from .steps import create_flow_steps

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def validate_message(message: Dict[str, Any], step: Dict[str, Any]) -> bool:
    """Validate message for current step"""
    try:
        text = message.get("text", "").strip()
        if not text:
            return False
        return step["validator"](text) if step.get("validator") else True
    except Exception:
        return False


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle incoming message with strict state validation"""
    try:
        # Get required data (StateManager validates)
        flow_data = state_manager.get("flow_data")

        if not flow_data:
            return handle_initial_message(state_manager)
        return handle_flow_message(state_manager, message, credex_service)

    except StateException as e:
        logger.error(f"Message handling error: {str(e)}")
        raise


def handle_initial_message(state_manager: Any) -> Dict[str, Any]:
    """Handle first message enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get channel (StateManager validates)
        channel = state_manager.get("channel")

        # Initialize flow data
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": "credex_flow",
                "step": 0,
                "current_step": "start",
                "data": {}
            }
        })
        if not success:
            raise StateException(f"Failed to update state: {error}")

        # Log success
        logger.info(f"Initialized credex flow for channel {channel['identifier']}")

        # Get first step message
        steps = create_flow_steps()
        return steps[0]["message"](state_manager)

    except StateException as e:
        logger.error(f"Initial message error: {str(e)}")
        raise


def handle_flow_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle message during flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate input
        if not isinstance(message, dict):
            raise StateException("Invalid message format")

        # Get required data (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")
        steps = create_flow_steps()
        current_step = steps[flow_data["step"]]

        # Validate input
        if not validate_message(message, current_step):
            raise StateException(f"Invalid {current_step['id']} format")

        # Update flow data
        new_flow_data = {
            "flow_type": flow_data["flow_type"],
            "step": flow_data["step"] + 1,
            "current_step": steps[flow_data["step"] + 1]["id"],
            "data": {
                **flow_data.get("data", {}),
                steps[flow_data["step"]]["id"]: message.get("text", "").strip()
            }
        }

        # Update state
        success, error = state_manager.update_state({"flow_data": new_flow_data})
        if not success:
            raise StateException(f"Failed to update flow data: {error}")

        # Log progress
        logger.info(f"Processed step {flow_data['step']} for channel {channel['identifier']}")

        # Get next step message or handle completion
        if flow_data["step"] + 1 < len(steps):
            return steps[flow_data["step"] + 1]["message"](state_manager)
        return handle_completion(state_manager, message, credex_service)

    except StateException as e:
        logger.error(f"Flow message error: {str(e)}")
        raise


def handle_completion(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle flow completion enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate input
        confirm = message.get("text", "").strip().lower()
        if confirm not in ["yes", "no"]:
            raise StateException("Please reply with yes or no")

        # Get channel (StateManager validates)
        channel = state_manager.get("channel")

        if confirm == "yes":
            # Process the credex operation
            result = credex_service['process_flow'](state_manager.get("flow_data"))
            if not result:
                raise StateException("Operation failed")

            # Transition to dashboard with success message
            success, error = state_manager.update_state({
                "flow_data": {
                    "flow_type": "dashboard",
                    "step": 0,
                    "current_step": "display",
                    "data": {
                        "message": "✅ Operation completed successfully!"
                    }
                }
            })
            if not success:
                raise StateException(f"Failed to transition flow: {error}")

            # Log success
            logger.info(f"Successfully completed credex flow for channel {channel['identifier']}")

        else:
            # Transition to dashboard with cancel message
            success, error = state_manager.update_state({
                "flow_data": {
                    "flow_type": "dashboard",
                    "step": 0,
                    "current_step": "display",
                    "data": {
                        "message": "Operation cancelled."
                    }
                }
            })
            if not success:
                raise StateException(f"Failed to transition flow: {error}")

            # Log cancellation
            logger.info(f"Cancelled credex flow for channel {channel['identifier']}")

        # Let dashboard handler show message
        from ...member.dashboard import handle_dashboard_display
        return handle_dashboard_display(state_manager)

    except StateException as e:
        logger.error(f"Completion error: {str(e)}")
        raise
