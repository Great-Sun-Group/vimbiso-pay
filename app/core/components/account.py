"""Account-related components

This module implements account-specific components with pure UI validation.
Business validation happens in services.
"""
from typing import Any, Dict

from core.utils.error_types import ValidationResult
from .base import Component


class AccountSelect(Component):
    """Account selection component"""

    def validate(self, value: Any) -> ValidationResult:
        """Validate account selection with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, str, "text")
        if not type_result.valid:
            return type_result

        # Validate required
        required_result = self._validate_required(value)
        if not required_result.valid:
            return required_result

        # Note: Business validation (available accounts) happens in service layer
        return ValidationResult.success(value.strip())

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        return {
            "account_id": value
        }


class LedgerDisplay(Component):
    """Ledger display component"""

    def validate(self, value: Any) -> ValidationResult:
        """Validate ledger data with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, dict, "object")
        if not type_result.valid:
            return type_result

        # Validate required fields
        required = ["entries"]
        missing = set(required) - set(value.keys())
        if missing:
            return ValidationResult.failure(
                message="Missing required ledger fields",
                field="ledger_data",
                details={
                    "missing_fields": list(missing),
                    "received_fields": list(value.keys())
                }
            )

        # Validate entries format
        entries = value["entries"]
        type_result = self._validate_type(entries, list, "array")
        if not type_result.valid:
            return ValidationResult.failure(
                message="Entries must be a list",
                field="entries",
                details={
                    "expected_type": "array",
                    "actual_type": str(type(entries))
                }
            )

        # Validate entry format
        required_entry = ["date", "description", "amount", "denom"]
        for i, entry in enumerate(entries):
            # Validate entry type
            if not isinstance(entry, dict):
                return ValidationResult.failure(
                    message="Invalid entry format",
                    field="entry",
                    details={
                        "index": i,
                        "expected_type": "object",
                        "actual_type": str(type(entry))
                    }
                )

            # Validate required entry fields
            missing = set(required_entry) - set(entry.keys())
            if missing:
                return ValidationResult.failure(
                    message="Missing required entry fields",
                    field="entry",
                    details={
                        "index": i,
                        "missing_fields": list(missing),
                        "received_fields": list(entry.keys())
                    }
                )

        return ValidationResult.success(value)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        return {
            "ledger_data": value
        }
