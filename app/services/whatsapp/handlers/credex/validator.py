"""Validator for credex flow states enforcing SINGLE SOURCE OF TRUTH"""
from typing import Dict, Any
from core.utils.validator_interface import ValidationResult
from core.utils.state_validator import StateValidator
from ...state_manager import StateManager


REQUIRED_FIELDS = {"member_id", "channel", "account_id"}


def validate_flow_data(flow_data: Dict[str, Any]) -> ValidationResult:
    """Validate credex flow data structure"""
    # First validate basic structure
    if not isinstance(flow_data, dict):
        return ValidationResult(
            is_valid=False,
            error_message="Flow data must be a dictionary"
        )

    if "id" not in flow_data:
        return ValidationResult(
            is_valid=False,
            error_message="Missing flow ID",
            missing_fields={"id"}
        )

    if "data" not in flow_data:
        return ValidationResult(
            is_valid=False,
            error_message="Missing flow data",
            missing_fields={"data"}
        )

    # Extract flow type from ID
    flow_id = flow_data["id"]
    flow_type = flow_id.split("_")[0] if "_" in flow_id else flow_id

    # Get data for flow-specific validation
    data = flow_data["data"]

    # Validate data based on flow type
    if flow_type == "offer":
        return validate_offer_data(data)
    elif flow_type == "cancel":
        return validate_cancel_data(data)
    elif flow_type in {"accept", "decline"}:
        return validate_action_data(data)

    return ValidationResult(is_valid=True)


def validate_flow_state(state: Dict[str, Any]) -> ValidationResult:
    """Validate complete flow state"""
    # First validate core state structure
    core_validation = StateValidator.validate_state(state)
    if not core_validation.is_valid:
        return core_validation

    # Check required fields at top level - SINGLE SOURCE OF TRUTH
    missing = REQUIRED_FIELDS - set(StateValidator.get_available_fields(state))
    if missing:
        return ValidationResult(
            is_valid=False,
            error_message=f"Missing required fields at top level: {', '.join(missing)}",
            missing_fields=missing
        )

    # Validate channel info at top level
    channel_validation = validate_channel_data(StateValidator.get_field(state, "channel", {}))
    if not channel_validation.is_valid:
        return channel_validation

    # Validate flow data if present
    flow_data = StateValidator.get_field(state, "flow_data", None)
    if flow_data is not None:
        return validate_flow_data(flow_data)

    return ValidationResult(is_valid=True)


def validate_channel_data(channel: Dict[str, Any]) -> ValidationResult:
    """Validate channel info structure"""
    required_fields = {"type", "identifier"}
    missing = required_fields - set(channel.keys())
    if missing:
        return ValidationResult(
            is_valid=False,
            error_message=f"Missing channel fields: {', '.join(missing)}",
            missing_fields=missing
        )

    # Validate channel type using StateManager
    channel_type = StateManager.get_channel_type({"channel": channel})
    if not channel_type:
        return ValidationResult(
            is_valid=False,
            error_message="Missing channel type"
        )

    if not isinstance(channel_type, str):
        return ValidationResult(
            is_valid=False,
            error_message="Channel type must be a string"
        )

    if channel_type != "whatsapp":
        return ValidationResult(
            is_valid=False,
            error_message="Invalid channel type"
        )

    # Validate channel identifier
    if not isinstance(channel["identifier"], str):
        return ValidationResult(
            is_valid=False,
            error_message="Channel identifier must be a string"
        )

    if not channel["identifier"]:
        return ValidationResult(
            is_valid=False,
            error_message="Missing channel identifier"
        )

    return ValidationResult(is_valid=True)


def validate_offer_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate offer-specific data"""
    required_fields = {"account_id"}  # Only require account_id in flow data
    missing = required_fields - set(data.keys())
    if missing:
        return ValidationResult(
            is_valid=False,
            error_message=f"Missing offer data fields: {', '.join(missing)}",
            missing_fields=missing
        )

    # Validate amount data if present
    if "amount_denom" in data:
        amount_data = data["amount_denom"]
        if not isinstance(amount_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Amount data must be a dictionary"
            )

        required_amount_fields = {"amount", "denomination"}
        missing_amount = required_amount_fields - set(amount_data.keys())
        if missing_amount:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing amount fields: {', '.join(missing_amount)}",
                missing_fields=missing_amount
            )

    return ValidationResult(is_valid=True)


def validate_cancel_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate cancel-specific data"""
    # For confirmation step, require credex_id
    if "credex_id" not in data and data.get("step", 0) > 0:
        return ValidationResult(
            is_valid=False,
            error_message="Missing credex_id for confirmation",
            missing_fields={"credex_id"}
        )

    return ValidationResult(is_valid=True)


def validate_action_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate accept/decline-specific data"""
    # For confirmation step, require credex_id
    if "credex_id" not in data and data.get("step", 0) > 0:
        return ValidationResult(
            is_valid=False,
            error_message="Missing credex_id for confirmation",
            missing_fields={"credex_id"}
        )

    return ValidationResult(is_valid=True)
