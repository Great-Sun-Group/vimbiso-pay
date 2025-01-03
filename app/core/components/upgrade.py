"""Upgrade components

This module implements upgrade-specific components following the component system pattern.
Each component handles a specific part of the upgrade flow with pure UI validation.
Business validation happens in services.
"""

from typing import Any, Dict

from core.utils.error_types import ValidationResult
from .base import Component


class UpgradeConfirm(Component):
    """Handles upgrade confirmation"""

    def __init__(self):
        super().__init__("upgrade_confirm")

    def validate(self, value: Any) -> ValidationResult:
        """Validate upgrade confirmation with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, dict, "object")
        if not type_result.valid:
            return type_result

        # Validate required fields
        required_fields = {"confirmed", "member_id", "account_id"}
        missing = required_fields - set(value.keys())
        if missing:
            return ValidationResult.failure(
                message="Missing required upgrade fields",
                field="data",
                details={
                    "missing_fields": list(missing),
                    "received_fields": list(value.keys())
                }
            )

        # Validate confirmation
        if not value["confirmed"]:
            return ValidationResult.failure(
                message="Upgrade must be confirmed",
                field="confirmed",
                details={
                    "expected": True,
                    "received": value["confirmed"]
                }
            )

        return ValidationResult.success(value)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified upgrade data"""
        return {
            "confirmed": True,
            "member_id": value["member_id"],
            "account_id": value["account_id"]
        }


class UpgradeComplete(Component):
    """Handles upgrade completion"""

    def __init__(self):
        super().__init__("upgrade_complete")

    def validate(self, value: Any) -> ValidationResult:
        """Validate upgrade response with proper tracking"""
        # Validate type
        type_result = self._validate_type(value, dict, "object")
        if not type_result.valid:
            return type_result

        # Validate required fields
        if "tier" not in value:
            return ValidationResult.failure(
                message="Missing tier in upgrade response",
                field="tier",
                details={
                    "missing_field": "tier",
                    "received_fields": list(value.keys())
                }
            )

        return ValidationResult.success(value)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified upgrade data"""
        return {
            "new_tier": value["tier"],
            "limits": value.get("limits", {}),
            "upgrade_complete": True
        }
