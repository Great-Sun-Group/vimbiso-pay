"""Unified state validation for flow management"""
import logging
from typing import Dict, Any
from .validator_interface import ValidationResult

logger = logging.getLogger(__name__)


class StateValidator:
    """Centralized state validation for core state structure"""

    CRITICAL_FIELDS = {
        "profile",
        "current_account",
        "jwt_token",
        "member_id",
        "account_id",
        "_validation_context",  # Add validation context tracking
        "_validation_state"     # Add validation state
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any], preserve_context: bool = True) -> ValidationResult:
        """
        Validate core state structure

        Args:
            state: State dictionary to validate
            preserve_context: Whether to preserve validation context in validation
        """
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Get required fields based on context preservation
        required_fields = cls.CRITICAL_FIELDS
        if not preserve_context:
            # Exclude context fields if not preserving
            required_fields = {
                f for f in required_fields
                if not f.startswith('_')
            }

        # Allow minimal state with just mobile_number and _last_updated during greeting
        if len(state) == 2 and "mobile_number" in state and "_last_updated" in state:
            return ValidationResult(is_valid=True)

        # For non-greeting states, check for required fields
        state_keys = set(state.keys())
        missing = required_fields - state_keys

        if missing:
            return ValidationResult(
                is_valid=False,
                error_message="Missing required fields: " + ", ".join(missing),
                missing_fields=missing
            )

        # Validate profile structure
        profile_validation = cls.validate_profile_structure(state.get("profile", {}))
        if not profile_validation.is_valid:
            return profile_validation

        # Validate current_account structure if not empty
        current_account = state.get("current_account", {})
        if current_account:  # Only validate if account has data
            account_validation = cls.validate_account_structure(current_account)
            if not account_validation.is_valid:
                return account_validation

        # Validate validation context if present and preserving
        if preserve_context and "_validation_context" in state:
            context = state["_validation_context"]
            if not isinstance(context, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Validation context must be a dictionary"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_profile_structure(cls, profile: Dict[str, Any]) -> ValidationResult:
        """Validate profile data structure"""
        if not isinstance(profile, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile must be a dictionary"
            )

        # Validate action structure
        action = profile.get("action", {})
        if not isinstance(action, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile action must be a dictionary"
            )

        # Ensure required action fields with defaults
        required_action_fields = {
            "id": "",
            "type": "",
            "timestamp": "",
            "actor": "",
            "details": {},
            "message": "",
            "status": ""
        }
        for field, default in required_action_fields.items():
            if field not in action:
                action[field] = default

        # Validate dashboard structure
        dashboard = profile.get("dashboard", {})
        if not isinstance(dashboard, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile dashboard must be a dictionary"
            )

        # Ensure required dashboard fields with defaults
        if "member" not in dashboard:
            dashboard["member"] = {}
        if "accounts" not in dashboard:
            dashboard["accounts"] = []

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_account_structure(cls, account: Dict[str, Any]) -> ValidationResult:
        """
        Validate account data structure
        Allows empty account during initialization
        """
        if not isinstance(account, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Account must be a dictionary"
            )

        # If account is empty, it's valid (initialization state)
        if not account:
            return ValidationResult(is_valid=True)

        # For non-empty accounts, check required fields
        required_fields = {
            "accountID", "accountName", "accountHandle",
            "accountType", "defaultDenom", "balanceData"
        }

        # Check if at least accountType and accountHandle are present
        minimal_fields = {"accountType", "accountHandle"}
        has_minimal_fields = all(field in account for field in minimal_fields)

        if has_minimal_fields:
            # If minimal fields present, it's a valid partial account
            return ValidationResult(is_valid=True)

        # For complete accounts, check all required fields
        missing = required_fields - set(account.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required account fields: {', '.join(missing)}",
                missing_fields=missing
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def ensure_profile_structure(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure profile has proper structure while preserving data"""
        if not isinstance(profile, dict):
            return {
                "action": {
                    "id": "",
                    "type": "",
                    "timestamp": "",
                    "actor": "",
                    "details": {},
                    "message": "",
                    "status": ""
                },
                "dashboard": {
                    "member": {},
                    "accounts": []
                }
            }

        result = profile.copy()

        # Ensure action structure
        if "action" not in result or not isinstance(result["action"], dict):
            result["action"] = {
                "id": "",
                "type": "",
                "timestamp": "",
                "actor": "",
                "details": {}
            }
        else:
            # Ensure all action fields exist
            action_fields = {
                "id": "",
                "type": "",
                "timestamp": "",
                "actor": "",
                "details": {},
                "message": "",
                "status": ""
            }
            for field, default in action_fields.items():
                if field not in result["action"]:
                    result["action"][field] = default
                elif field == "details" and not isinstance(result["action"][field], dict):
                    result["action"][field] = {}

        # Ensure dashboard structure
        if "dashboard" not in result or not isinstance(result["dashboard"], dict):
            result["dashboard"] = {
                "member": {},
                "accounts": []
            }
        else:
            # Ensure required dashboard fields
            if "member" not in result["dashboard"]:
                result["dashboard"]["member"] = {}
            if "accounts" not in result["dashboard"]:
                result["dashboard"]["accounts"] = []
            elif not isinstance(result["dashboard"]["accounts"], list):
                result["dashboard"]["accounts"] = []

        return result

    @classmethod
    def ensure_validation_context(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure validation context structure while preserving data"""
        if not isinstance(state, dict):
            return {}

        result = state.copy()

        # Initialize validation context if not present
        if "_validation_context" not in result:
            result["_validation_context"] = {}
        elif not isinstance(result["_validation_context"], dict):
            result["_validation_context"] = {}

        # Initialize validation state if not present
        if "_validation_state" not in result:
            result["_validation_state"] = {}
        elif not isinstance(result["_validation_state"], dict):
            result["_validation_state"] = {}

        return result
