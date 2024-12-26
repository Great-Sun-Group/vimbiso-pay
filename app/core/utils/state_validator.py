"""Unified state validation for flow management"""
import logging
from typing import Dict, Any
from .validator_interface import ValidationResult

logger = logging.getLogger(__name__)


class StateValidator:
    """Centralized state validation for core state structure"""

    CRITICAL_FIELDS = {
        "member_id",    # Primary identifier
        "channel",      # Channel information
        "profile",      # User profile
        "account_id",   # Account reference
        "flow_data"     # Flow state
    }

    CHANNEL_FIELDS = {
        "type",         # Channel type (e.g. whatsapp)
        "identifier",   # Channel-specific identifier
        "metadata"      # Channel-specific metadata
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any], preserve_context: bool = True) -> ValidationResult:
        """
        Validate core state structure and enforce SINGLE SOURCE OF TRUTH

        Args:
            state: State dictionary to validate
            preserve_context: Whether to preserve validation context in validation
        """
        # First convert legacy mobile_number to channel identifier
        if "mobile_number" in state and "channel" not in state:
            state["channel"] = {
                "type": "whatsapp",
                "identifier": state["mobile_number"],
                "metadata": {}
            }
            del state["mobile_number"]
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

        # Validate and enforce channel structure, even during greeting
        if "channel" in state:
            channel_validation = cls.validate_channel_structure(state["channel"])
            if not channel_validation.is_valid:
                return channel_validation

            # Ensure no duplicate channel info in flow_data
            if "flow_data" in state and isinstance(state["flow_data"], dict):
                flow_data = state["flow_data"]
                if "data" in flow_data and isinstance(flow_data["data"], dict):
                    if "channel" in flow_data["data"]:
                        del flow_data["data"]["channel"]
                    if "mobile_number" in flow_data["data"]:
                        del flow_data["data"]["mobile_number"]

        # Allow minimal state during greeting but ensure proper structure
        if not state.get("authenticated", False):
            # Even during greeting, ensure channel info is present
            if "channel" not in state or not isinstance(state["channel"], dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel info must be present even during greeting"
                )

            # Validate channel structure
            channel_validation = cls.validate_channel_structure(state["channel"])
            if not channel_validation.is_valid:
                return channel_validation

            # Allow other fields to be missing during greeting
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

        # Validate member_id is at top level - SINGLE SOURCE OF TRUTH
        if "member_id" not in state:
            return ValidationResult(
                is_valid=False,
                error_message="member_id must be present at top level as the SINGLE SOURCE OF TRUTH"
            )

        # Ensure no duplicate member_id in flow_data
        if "flow_data" in state and isinstance(state["flow_data"], dict):
            flow_data = state["flow_data"]
            if "data" in flow_data and isinstance(flow_data["data"], dict):
                if "member_id" in flow_data["data"]:
                    del flow_data["data"]["member_id"]

        # Validate flow data if present
        if "flow_data" in state:
            flow_validation = cls.validate_flow_data_structure(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_flow_data_structure(cls, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate flow data structure"""
        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Check required flow fields
        required_fields = {"id", "step", "data"}
        missing = required_fields - set(flow_data.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required flow fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate step is a non-negative integer
        if not isinstance(flow_data["step"], int) or flow_data["step"] < 0:
            return ValidationResult(
                is_valid=False,
                error_message="Step must be a non-negative integer"
            )

        # Validate flow data structure
        data = flow_data.get("data", {})
        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Ensure validation state exists but don't validate its structure
        if "_validation_state" not in data:
            data["_validation_state"] = {}

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_profile_structure(cls, profile: Dict[str, Any]) -> ValidationResult:
        """Validate profile data structure"""
        if not isinstance(profile, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile must be a dictionary"
            )

        # Only validate structure existence, not content
        if "action" in profile and not isinstance(profile["action"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile action must be a dictionary"
            )

        if "dashboard" in profile and not isinstance(profile["dashboard"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Profile dashboard must be a dictionary"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_channel_structure(cls, channel: Dict[str, Any]) -> ValidationResult:
        """Validate channel information structure"""
        if not isinstance(channel, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel must be a dictionary"
            )

        # Check required channel fields
        missing = cls.CHANNEL_FIELDS - set(channel.keys())
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required channel fields: {', '.join(missing)}",
                missing_fields=missing
            )

        # Validate channel type
        if not isinstance(channel["type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Channel type must be a string"
            )

        # Validate metadata is a dictionary
        if not isinstance(channel["metadata"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel metadata must be a dictionary"
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

        # Only validate minimal fields if account is not empty
        if account:
            minimal_fields = {"accountType", "accountHandle"}
            missing = minimal_fields - set(account.keys())
            if missing:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Missing required account fields: {', '.join(missing)}",
                    missing_fields=missing
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def ensure_profile_structure(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure minimal profile structure while preserving data"""
        if not isinstance(profile, dict):
            return {
                "action": {},
                "dashboard": {"accounts": []}
            }

        result = profile.copy()

        # Ensure basic structure exists
        if "action" not in result or not isinstance(result["action"], dict):
            result["action"] = {}

        if "dashboard" not in result or not isinstance(result["dashboard"], dict):
            result["dashboard"] = {"accounts": []}
        elif "accounts" not in result["dashboard"]:
            result["dashboard"]["accounts"] = []
        elif not isinstance(result["dashboard"]["accounts"], list):
            result["dashboard"]["accounts"] = []

        return result

    @classmethod
    def ensure_validation_context(cls, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure minimal validation context structure"""
        result = flow_data if isinstance(flow_data, dict) else {}

        # Ensure data dictionary exists
        if "data" not in result or not isinstance(result["data"], dict):
            result["data"] = {}

        # Initialize validation state if needed
        if not isinstance(result["data"].get("_validation_state"), dict):
            result["data"]["_validation_state"] = {}

        return result
