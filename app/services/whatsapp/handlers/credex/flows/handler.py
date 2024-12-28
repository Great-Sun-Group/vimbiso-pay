"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle incoming message with strict state validation"""
    try:
        # Let StateManager validate flow state

        # Process current step (StateManager validates flow_data structure)
        current_step = state_manager.get("flow_data")["current_step"]
        if current_step == "complete":
            return handle_completion(state_manager, message, credex_service)

        # Default to next step
        return handle_next_step(state_manager, message, credex_service)

    except StateException as e:
        logger.error(f"Message handling error: {str(e)}")
        raise


def handle_next_step(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle next step in flow"""
    try:
        # Let StateManager determine next message
        return state_manager.get_message("next")

    except StateException as e:
        logger.error(f"Next step error: {str(e)}")
        raise


def handle_completion(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle flow completion"""
    try:
        # Let StateManager determine completion message
        return state_manager.get_message("complete")

    except StateException as e:
        logger.error(f"Completion error: {str(e)}")
        raise
