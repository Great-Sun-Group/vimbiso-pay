"""Unified state validation for flow management"""
import logging
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of state validation"""
    is_valid: bool
    error_message: Optional[str] = None
    missing_fields: Set[str] = None

    def __bool__(self):
        return self.is_valid


class StateValidator:
    """Centralized state validation"""

    CRITICAL_FIELDS = {
        "profile",
        "current_account",
        "jwt_token"
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete state structure"""
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Check for required fields
        missing = cls.CRITICAL_FIELDS - set(state.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message="Missing required fields: " + ", ".join(missing),
                missing_fields=missing
            )

        # Validate profile structure
        profile_validation = cls.validate_profile_structure(state.get("profile", {}))
        if not profile_validation:
            return profile_validation

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_profile_structure(cls, profile: Dict[str, Any]) -> ValidationResult:
        """Validate profile data structure"""
        if not isinstance(profile, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile must be a dictionary"
            )

        # Validate data structure
        data = profile.get("data", {})
        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile data must be a dictionary"
            )

        # Validate action structure
        action = data.get("action", {})
        if not isinstance(action, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile action must be a dictionary"
            )

        # Validate details structure
        details = action.get("details", {})
        if not isinstance(details, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile details must be a dictionary"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def ensure_profile_structure(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure profile has proper structure while preserving data"""
        if not isinstance(profile, dict):
            return {
                "data": {
                    "action": {
                        "details": {}
                    }
                }
            }

        result = profile.copy()

        # Ensure data structure
        if "data" not in result:
            result["data"] = {}
        elif not isinstance(result["data"], dict):
            result["data"] = {}

        # Ensure action structure
        if "action" not in result["data"]:
            result["data"]["action"] = {}
        elif not isinstance(result["data"]["action"], dict):
            result["data"]["action"] = {}

        # Ensure details structure
        if "details" not in result["data"]["action"]:
            result["data"]["action"]["details"] = {}
        elif not isinstance(result["data"]["action"]["details"], dict):
            result["data"]["action"]["details"] = {}

        return result

    @classmethod
    def validate_flow_state(cls, state: Dict[str, Any], required_fields: Set[str] = None) -> ValidationResult:
        """Validate flow-specific state"""
        # Start with basic state validation
        basic_validation = cls.validate_state(state)
        if not basic_validation:
            return basic_validation

        # Check flow-specific required fields
        if required_fields:
            missing = required_fields - set(state.keys())
            if missing:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing flow-specific fields: " + ", ".join(missing),
                    missing_fields=missing
                )

        return ValidationResult(is_valid=True)
