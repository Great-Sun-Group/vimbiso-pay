"""Upgrade components

This module implements upgrade-specific components following the component system pattern.
Each component handles a specific part of the upgrade flow with clear validation and conversion.
"""

from typing import Any, Dict

from core.utils.exceptions import ComponentException
from .base import Component


class UpgradeConfirm(Component):
    """Handles upgrade confirmation"""

    def __init__(self):
        super().__init__("upgrade_confirm")

    def validate(self, value: Any) -> Dict:
        """Validate upgrade confirmation

        Args:
            value: Dictionary containing:
                - confirmed: Boolean confirmation
                - member_id: Member ID
                - account_id: Account ID

        Returns:
            On success: {"valid": True}
            On error: ComponentException
        """
        # Validate type
        if not isinstance(value, dict):
            raise ComponentException(
                message="Invalid upgrade data format",
                component=self.type,
                field="data",
                value=str(type(value))
            )

        # Validate required fields
        if not value.get("confirmed"):
            raise ComponentException(
                message="Upgrade must be confirmed",
                component=self.type,
                field="confirmed",
                value=str(value.get("confirmed"))
            )

        if not value.get("member_id"):
            raise ComponentException(
                message="Member ID required for upgrade",
                component=self.type,
                field="member_id",
                value=str(value.get("member_id"))
            )

        if not value.get("account_id"):
            raise ComponentException(
                message="Account ID required for upgrade",
                component=self.type,
                field="account_id",
                value=str(value.get("account_id"))
            )

        return {"valid": True}

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

    def validate(self, value: Any) -> Dict:
        """Validate upgrade response

        Args:
            value: Upgrade response containing:
                - tier: New tier level
                - limits: Updated tier limits

        Returns:
            On success: {"valid": True}
            On error: ComponentException
        """
        if not isinstance(value, dict):
            raise ComponentException(
                message="Invalid upgrade response format",
                component=self.type,
                field="response",
                value=str(type(value))
            )

        # Validate required fields
        if "tier" not in value:
            raise ComponentException(
                message="Missing tier in upgrade response",
                component=self.type,
                field="tier",
                value=str(value)
            )

        return {"valid": True}

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified upgrade data"""
        return {
            "new_tier": value["tier"],
            "limits": value.get("limits", {}),
            "upgrade_complete": True
        }
