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

    # State schema defining expected structure
    STATE_SCHEMA = {
        # Channel info needed for messaging
        "channel": {
            "type": dict,
            "required": ["type", "identifier"],
            "fields": {
                "type": str,
                "identifier": str
            }
        },

        # Auth state
        "auth": {
            "type": dict,
            "required": ["token"],
            "fields": {
                "token": str
            }
        },

        # Dashboard data from API
        "dashboard": {
            "type": dict,
            "required": ["member"],
            "fields": {
                "member": {
                    "type": dict,
                    "required": ["memberID", "memberTier", "firstname", "lastname", "memberHandle", "defaultDenom"],
                    "fields": {
                        "memberID": str,
                        "memberTier": int,
                        "firstname": str,
                        "lastname": str,
                        "memberHandle": str,
                        "defaultDenom": str,
                        "remainingAvailableUSD": (type(None), float)
                    }
                },
                "accounts": {
                    "type": list,
                    "item_fields": {
                        "type": dict,
                        "required": ["accountID", "accountName", "accountHandle", "accountType", "defaultDenom", "isOwnedAccount"],
                        "fields": {
                            "accountID": str,
                            "accountName": str,
                            "accountHandle": str,
                            "accountType": str,
                            "defaultDenom": str,
                            "isOwnedAccount": bool,
                            "sendOffersTo": {
                                "type": dict,
                                "required": ["memberID", "firstname", "lastname"],
                                "fields": {
                                    "memberID": str,
                                    "firstname": str,
                                    "lastname": str
                                }
                            },
                            "balanceData": {
                                "type": dict,
                                "required": ["securedNetBalancesByDenom", "unsecuredBalancesInDefaultDenom", "netCredexAssetsInDefaultDenom"],
                                "fields": {
                                    "securedNetBalancesByDenom": list,
                                    "unsecuredBalancesInDefaultDenom": {
                                        "type": dict,
                                        "required": ["totalPayables", "totalReceivables", "netPayRec"],
                                        "fields": {
                                            "totalPayables": str,
                                            "totalReceivables": str,
                                            "netPayRec": str
                                        }
                                    },
                                    "netCredexAssetsInDefaultDenom": str
                                }
                            },
                            "pendingInData": {
                                "type": list,
                                "item_fields": {
                                    "type": dict,
                                    "required": ["credexID", "formattedInitialAmount", "counterpartyAccountName"],
                                    "fields": {
                                        "credexID": str,
                                        "formattedInitialAmount": str,
                                        "counterpartyAccountName": str,
                                        "dueDate": (type(None), str),
                                        "secured": (type(None), bool)
                                    }
                                }
                            },
                            "pendingOutData": {
                                "type": list,
                                "item_fields": {
                                    "type": dict,
                                    "required": ["credexID", "formattedInitialAmount", "counterpartyAccountName"],
                                    "fields": {
                                        "credexID": str,
                                        "formattedInitialAmount": str,
                                        "counterpartyAccountName": str,
                                        "dueDate": (type(None), str),
                                        "secured": (type(None), bool)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },

        # Action data from API
        "action": {
            "type": dict,
            "required": ["id", "type", "timestamp", "actor", "details"],
            "fields": {
                "id": str,
                "type": str,
                "timestamp": str,
                "actor": str,
                "details": dict
            }
        },

        # Active account selection
        "active_account_id": {
            "type": str
        },

        # Flow state
        "component_data": {
            "type": dict,
            "required": ["path", "component", "data"],
            "fields": {
                "path": str,          # Flow path
                "component": str,     # Current component
                "component_result": (type(None), str),  # Optional flow control
                "awaiting_input": bool,  # Optional input state
                "data": dict         # Component-specific data
            }
        },

        # Mock testing flag
        "mock_testing": {
            "type": bool
        }
    }

    @classmethod
    def _validate_field(cls, field_name: str, field_value: Any, field_schema: dict) -> ValidationResult:
        """Validate a field against its schema"""
        # Check type
        if isinstance(field_schema, dict):
            if not isinstance(field_value, field_schema["type"]):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field_name} must be a {field_schema['type'].__name__}"
                )

            # For dictionaries, validate required fields and field types
            if field_schema["type"] == dict:
                # Check required fields
                if "required" in field_schema:
                    for required_field in field_schema["required"]:
                        if required_field not in field_value:
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"Missing required field in {field_name}: {required_field}"
                            )

                # Validate field types
                if "fields" in field_schema:
                    for sub_field, sub_value in field_value.items():
                        if sub_field in field_schema["fields"]:
                            sub_schema = field_schema["fields"][sub_field]
                            result = cls._validate_field(f"{field_name}.{sub_field}", sub_value, sub_schema)
                            if not result.is_valid:
                                return result

            # For lists, validate item fields if specified
            elif field_schema["type"] == list and "item_fields" in field_schema:
                for i, item in enumerate(field_value):
                    result = cls._validate_field(f"{field_name}[{i}]", item, field_schema["item_fields"])
                    if not result.is_valid:
                        return result

        # For simple type checking
        elif isinstance(field_schema, type) and not isinstance(field_value, field_schema):
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} must be a {field_schema.__name__}"
            )

        # For tuple of types (optional fields)
        elif isinstance(field_schema, tuple):
            if not any(isinstance(field_value, t) for t in field_schema):
                type_names = " or ".join(t.__name__ for t in field_schema)
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field_name} must be {type_names}"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate state against schema"""
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate each field against schema
        for field_name, field_schema in cls.STATE_SCHEMA.items():
            if field_name in state:
                result = cls._validate_field(field_name, state[field_name], field_schema)
                if not result.is_valid:
                    return result

        return ValidationResult(is_valid=True)

    @classmethod
    def prepare_state_update(cls, state_manager: Any, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and prepare state updates

        Args:
            state_manager: StateManager instance
            updates: State updates to apply

        Returns:
            Validated state updates

        Raises:
            ComponentException: If updates are invalid
        """
        from core.error.exceptions import ComponentException

        # Validate against schema
        result = cls.validate_state(updates)
        if not result.is_valid:
            raise ComponentException(
                message=result.error_message,
                component="state_validator",
                field="state_schema"
            )

        return updates
