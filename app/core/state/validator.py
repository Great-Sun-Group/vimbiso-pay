"""State validation

This module provides schema validation for state data structure.
Components handle their own data validation.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ValidationResult:
    """Result of state validation"""
    is_valid: bool
    error_message: Optional[str] = None


class StateValidator:
    """Validates state structure against schema"""

    # State schema defining field types when present
    STATE_SCHEMA = {
        # Required initially - channel info for messaging
        "channel": {
            "type": dict,
            "fields": {
                "type": {"type": str},      # Channel type (e.g. "whatsapp", "sms")
                "identifier": {"type": str}  # Channel ID (e.g. phone number)
            },
            "required": ["type", "identifier"]
        },

        # Required flag for mock testing mode
        "mock_testing": {"type": bool},

        # Added during login
        "auth": {
            "type": dict,
            "fields": {
                "token": {"type": str}
            }
        },

        # Added during login/onboarding and update with (almost) every API call
        "dashboard": {
            "type": dict,
            "fields": {
                "member": {
                    "type": dict,
                    "fields": {
                        "memberID": {"type": str},
                        "memberTier": {"type": int},
                        "firstname": {"type": str},
                        "lastname": {"type": str},
                        "memberHandle": {"type": str},
                        "defaultDenom": {"type": str},
                        "remainingAvailableUSD": {"type": float}
                    }
                },
                "accounts": {
                    "type": list,
                    "item_fields": {
                        "type": dict,
                        "fields": {
                            "accountID": {"type": str},
                            "accountName": {"type": str},
                            "accountHandle": {"type": str},
                            "accountType": {"type": str},
                            "defaultDenom": {"type": str},
                            "isOwnedAccount": {"type": bool}
                        }
                    }
                }
            }
        },

        # Added/updated on every API call
        "action": {
            "type": dict,
            "fields": {
                "id": {"type": str},
                "type": {"type": str},
                "timestamp": {"type": str},
                "actor": {"type": str},
                "details": {"type": dict}
            }
        },

        # Added during account selection or by default
        "active_account_id": {"type": str},

        # Used internally by components
        # Used for component-to-flow communication
        # Used to pass Message data to component for member control of component operations
        # Wiped on component initialization for clean slate
        "component_data": {
            "type": dict,
            "fields": {
                # Optional fields - validated only if present
                "path": {"type": str},
                "component": {"type": str},
                "component_result": {"type": (str, type(None))},
                "awaiting_input": {"type": bool},
                "data": {"type": dict},
                # Message structure - validated only if present
                "incoming_message": {
                    "type": dict,
                    "fields": {
                        "type": {"type": str},
                        "text": {"type": dict}  # Structure varies by type
                    }
                }
            }
        }
    }

    @classmethod
    def _validate_field(cls, field_name: str, field_value: Any, field_schema: dict) -> ValidationResult:
        """Validate a field against its schema"""
        # Handle both simple type and schema dict formats
        field_type = field_schema["type"] if isinstance(field_schema, dict) and "type" in field_schema else field_schema

        # Validate type - handle both single type and tuple of allowed types
        if isinstance(field_type, tuple):
            if not any(isinstance(field_value, t) for t in field_type):
                allowed_types = " or ".join(t.__name__ for t in field_type)
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field_name} must be a {allowed_types}"
                )
        else:
            if not isinstance(field_value, field_type):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field_name} must be a {field_type.__name__}"
                )

        # For dictionaries, validate field types
        if isinstance(field_value, dict) and "fields" in field_schema:
            # Check required fields first
            if "required" in field_schema:
                for required_field in field_schema["required"]:
                    if required_field not in field_value:
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Required field missing: {field_name}.{required_field}"
                        )

            # Then validate each field
            for sub_field, sub_value in field_value.items():
                if sub_field in field_schema["fields"]:
                    sub_schema = field_schema["fields"][sub_field]
                    result = cls._validate_field(f"{field_name}.{sub_field}", sub_value, sub_schema)
                    if not result.is_valid:
                        return result

        # For lists, validate item fields if specified
        if isinstance(field_value, list) and "item_fields" in field_schema:
            for i, item in enumerate(field_value):
                result = cls._validate_field(f"{field_name}[{i}]", item, field_schema["item_fields"])
                if not result.is_valid:
                    return result

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_jwt(cls, jwt_token: str) -> bool:
        """Validate JWT token is not expired"""
        from decouple import config
        from jwt import InvalidTokenError, decode
        try:
            decode(jwt_token, config("JWT_SECRET"), algorithms=["HS256"])
            return True
        except InvalidTokenError:
            return False

    @classmethod
    def _validate_dependencies(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate state field dependencies and completeness"""
        # Channel is required for JWT
        auth = state.get("auth", {})
        if auth and "token" in auth:
            channel = state.get("channel")
            if not channel or not isinstance(channel, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel info is required for authentication"
                )
            if not channel.get("type") or not channel.get("identifier"):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel type and identifier are required for authentication"
                )

        # Valid JWT is required for other fields
        jwt_token = auth.get("token")
        if not jwt_token:
            # Only allow channel and mock_testing without JWT
            for field in state:
                if field not in ["channel", "mock_testing", "auth"]:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Authentication required for {field}"
                    )
        elif not cls._validate_jwt(jwt_token):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid or expired authentication token"
            )

        # Dashboard requires complete member data and personal account
        dashboard = state.get("dashboard")
        if dashboard:
            member = dashboard.get("member", {})
            if not all(field in member for field in [
                "memberID", "memberTier", "firstname", "lastname",
                "memberHandle", "defaultDenom", "remainingAvailableUSD"
            ]):
                return ValidationResult(
                    is_valid=False,
                    error_message="Incomplete member data in dashboard"
                )

            accounts = dashboard.get("accounts", [])
            has_personal = any(
                account.get("accountType") == "personal" and
                all(field in account for field in [
                    "accountID", "accountName", "accountHandle",
                    "accountType", "defaultDenom", "isOwnedAccount"
                ])
                for account in accounts
            )
            if not has_personal:
                return ValidationResult(
                    is_valid=False,
                    error_message="Dashboard requires a complete personal account"
                )

        # Action requires all fields
        action = state.get("action")
        if action and not all(field in action for field in ["id", "type", "timestamp", "actor", "details"]):
            return ValidationResult(
                is_valid=False,
                error_message="Incomplete action data"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_state(cls, state: Dict[str, Any], full_validation: bool = False) -> ValidationResult:
        """Validate state against schema and dependencies

        Args:
            state: State dictionary to validate
            full_validation: If True, validates all schema fields exist and match types
                           If False, only validates fields present in state

        Returns:
            ValidationResult indicating if state is valid
        """
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Get fields to validate
        fields_to_validate = cls.STATE_SCHEMA.keys() if full_validation else state.keys()

        # Validate each field against schema
        for field_name in fields_to_validate:
            # Check field exists in schema
            if field_name not in cls.STATE_SCHEMA:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unknown field: {field_name}"
                )

            # Get field value
            field_value = state.get(field_name)

            # Skip validation if field is None (allows clearing fields)
            if field_value is None:
                continue

            # Validate field type and structure
            result = cls._validate_field(field_name, field_value, cls.STATE_SCHEMA[field_name])
            if not result.is_valid:
                return result

        # For full validation, also validate dependencies
        if full_validation:
            result = cls._validate_dependencies(state)
            if not result.is_valid:
                return result

        return ValidationResult(is_valid=True)

    @classmethod
    def prepare_state_update(cls, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate state updates

        Args:
            updates: State updates to apply

        Returns:
            Validated state updates

        Raises:
            ComponentException: If updates are invalid
        """
        from core.error.exceptions import ComponentException

        # Validate updates
        result = cls.validate_state(updates, full_validation=False)
        if not result.is_valid:
            raise ComponentException(
                message=result.error_message,
                component="state_validator",
                field="state_schema",
                value=str(updates)
            )

        return updates
