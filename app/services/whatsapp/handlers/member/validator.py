"""Validator for member flow states enforcing SINGLE SOURCE OF TRUTH"""
from typing import Dict, Any

from core.utils.state_validator import StateValidator
from core.utils.validator_interface import ValidationResult


REQUIRED_FIELDS = {"member_id", "channel"}


def validate_flow_data(flow_data: Dict[str, Any]) -> ValidationResult:
    """Validate member flow data structure"""
    if not isinstance(flow_data, dict):
        return ValidationResult(
            is_valid=False,
            error_message="Flow data must be a dictionary"
        )

    # Empty flow data is valid for initial state
    if not flow_data:
        return ValidationResult(is_valid=True)

    # Validate required fields
    required_fields = {"id", "step", "data"}
    missing = required_fields - set(flow_data.keys())
    if missing:
        return ValidationResult(
            is_valid=False,
            error_message=f"Missing required flow fields: {', '.join(missing)}",
            missing_fields=missing
        )

    # Validate flow type
    if flow_data["id"] not in {"member_registration", "member_upgrade"}:
        return ValidationResult(
            is_valid=False,
            error_message="Invalid member flow type"
        )

    # Validate step
    if not isinstance(flow_data["step"], int) or flow_data["step"] < 0:
        return ValidationResult(
            is_valid=False,
            error_message="Invalid step value"
        )

    # Validate flow-specific data
    data = flow_data["data"]
    if not isinstance(data, dict):
        return ValidationResult(
            is_valid=False,
            error_message="Flow data must be a dictionary"
        )

    # Validate data based on flow type
    if flow_data["id"] == "member_registration":
        return validate_registration_data(data)
    elif flow_data["id"] == "member_upgrade":
        return validate_upgrade_data(data)

    return ValidationResult(is_valid=True)


def validate_flow_state(state: Dict[str, Any]) -> ValidationResult:
    """Validate complete flow state"""
    # First validate core state structure
    validation = StateValidator.validate_state(state)
    if not validation.is_valid:
        return validation

    # Then validate flow-specific requirements
    validation = StateValidator.validate_before_access(state, REQUIRED_FIELDS)
    if not validation.is_valid:
        return validation

    # Validate flow data if present
    flow_data = StateValidator.get_field(state, "flow_data", None)
    if flow_data is not None:
        flow_validation = validate_flow_data(flow_data)
        if not flow_validation.is_valid:
            return flow_validation

    return ValidationResult(is_valid=True)


def validate_before_access(state: Dict[str, Any], required_fields: set[str]) -> ValidationResult:
    """Validate state before field access"""
    # First validate core state
    validation = StateValidator.validate_state(state)
    if not validation.is_valid:
        return validation

    # Then validate required fields
    return StateValidator.validate_before_access(state, required_fields)


def validate_registration_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate registration-specific data"""
    # Validate name data if present
    if "first_name" in data:
        first_name = data["first_name"]
        if not isinstance(first_name, dict) or "first_name" not in first_name:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid first name data structure"
            )

    if "last_name" in data:
        last_name = data["last_name"]
        if not isinstance(last_name, dict) or "last_name" not in last_name:
            return ValidationResult(
                is_valid=False,
                error_message="Invalid last name data structure"
            )

    return ValidationResult(is_valid=True)


def validate_upgrade_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate upgrade-specific data"""
    # Only account_id required in flow data
    required_fields = {"account_id"}
    missing = required_fields - set(data.keys())
    if missing:
        return ValidationResult(
            is_valid=False,
            error_message=f"Missing upgrade data fields: {', '.join(missing)}",
            missing_fields=missing
        )

    return ValidationResult(is_valid=True)
