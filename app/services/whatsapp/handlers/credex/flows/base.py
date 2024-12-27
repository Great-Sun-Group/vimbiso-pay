"""Core credex flow functions enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

# Required fields for all credex flows
REQUIRED_FIELDS = {"channel", "member_id", "account_id", "authenticated", "jwt_token"}


def validate_credex_service(credex_service: Any) -> None:
    """Validate service has required capabilities"""
    if not credex_service:
        raise ValueError("Service not initialized")

    if not isinstance(credex_service, dict):
        raise ValueError("Invalid service format")

    # Check for required functions based on service.py implementation
    required_functions = {
        'validate_handle',  # member service
        'get_credex',      # offers service
        'offer_credex'     # offers service
    }
    # Since credex_service is a dict, we can use dict methods directly
    missing = required_functions - set(credex_service)
    if missing:
        raise ValueError(f"Service missing required functions: {', '.join(missing)}")


def validate_flow_state(state_manager: Any, flow_id: str) -> None:
    """Validate flow state enforcing SINGLE SOURCE OF TRUTH"""
    # Validate state access at boundary
    validation = StateValidator.validate_before_access(
        {field: state_manager.get(field) for field in REQUIRED_FIELDS},
        REQUIRED_FIELDS
    )
    if not validation.is_valid:
        raise ValueError(validation.error_message)

    # Log validation
    audit.log_flow_event(
        flow_id,
        "state_validation",
        None,
        {"channel_id": state_manager.get("channel")["identifier"]},
        "success"
    )


def process_flow_step(
    state_manager: Any,
    flow_id: str,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Dict[str, Any]:
    """Process a flow step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state and service
        validate_flow_state(state_manager, flow_id)
        if credex_service:
            validate_credex_service(credex_service)

        # Get flow data
        flow_data = state_manager.get("flow_data")
        if not isinstance(flow_data, dict):
            flow_data = {}

        # Process step (to be implemented by specific flow handlers)
        return {
            "flow_id": flow_id,
            "step": step,
            "flow_data": flow_data,
            "input_data": input_data,
            "credex_service": credex_service
        }

    except ValueError as e:
        logger.error(f"Flow step processing error: {str(e)}")
        raise
