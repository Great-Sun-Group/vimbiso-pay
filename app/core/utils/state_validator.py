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
        "account_id"
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate core state structure"""
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
        if not profile_validation.is_valid:
            return profile_validation

        # Validate current_account structure
        account_validation = cls.validate_account_structure(state.get("current_account", {}))
        if not account_validation.is_valid:
            return account_validation

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
        action = profile.get("action")
        if not isinstance(action, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile action must be a dictionary"
            )

        required_action_fields = {"id", "type", "timestamp", "actor", "details"}
        missing_action = required_action_fields - set(action.keys())
        if missing_action:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required action fields: {', '.join(missing_action)}",
                missing_fields=missing_action
            )

        # Validate dashboard structure
        dashboard = profile.get("dashboard")
        if not isinstance(dashboard, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile dashboard must be a dictionary"
            )

        required_dashboard_fields = {"member", "accounts"}
        missing_dashboard = required_dashboard_fields - set(dashboard.keys())
        if missing_dashboard:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required dashboard fields: {', '.join(missing_dashboard)}",
                missing_fields=missing_dashboard
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_account_structure(cls, account: Dict[str, Any]) -> ValidationResult:
        """Validate account data structure"""
        if not isinstance(account, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Account must be a dictionary"
            )

        required_fields = {
            "accountID", "accountName", "accountHandle",
            "accountType", "defaultDenom", "balanceData"
        }
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
                    "details": {}
                },
                "dashboard": {
                    "member": {},
                    "accounts": []
                }
            }

        result = profile.copy()

        # Ensure action structure
        if "action" not in result:
            result["action"] = {
                "id": "",
                "type": "",
                "timestamp": "",
                "actor": "",
                "details": {}
            }
        elif not isinstance(result["action"], dict):
            result["action"] = {
                "id": "",
                "type": "",
                "timestamp": "",
                "actor": "",
                "details": {}
            }

        # Ensure dashboard structure
        if "dashboard" not in result:
            result["dashboard"] = {
                "member": {},
                "accounts": []
            }
        elif not isinstance(result["dashboard"], dict):
            result["dashboard"] = {
                "member": {},
                "accounts": []
            }

        return result
