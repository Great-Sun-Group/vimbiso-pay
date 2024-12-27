"""Core credex flow functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def validate_credex_service(credex_service: Any) -> None:
    """Validate service has required capabilities"""
    if not credex_service:
        raise StateException("Service not initialized")

    if not isinstance(credex_service, dict):
        raise StateException("Invalid service format")

    # Check for required functions based on service.py implementation
    required_functions = {
        'validate_handle',  # member service
        'get_credex',      # offers service
        'offer_credex'     # offers service
    }
    # Since credex_service is a dict, we can use dict methods directly
    missing = required_functions - set(credex_service)
    if missing:
        raise StateException(f"Service missing required functions: {', '.join(missing)}")


def process_flow_step(
    state_manager: Any,
    flow_id: str,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Dict[str, Any]:
    """Process a flow step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required state (StateManager validates)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        # Log validation
        audit.log_flow_event(
            flow_id,
            "state_validation",
            None,
            {"channel_id": channel["identifier"]},
            "success"
        )

        # Validate service if provided
        if credex_service:
            validate_credex_service(credex_service)

        # Return step data for handler
        return {
            "flow_id": flow_id,
            "step": step,
            "flow_data": flow_data,
            "input_data": input_data,
            "credex_service": credex_service
        }

    except StateException as e:
        logger.error(f"Flow step processing error: {str(e)}")
        raise
