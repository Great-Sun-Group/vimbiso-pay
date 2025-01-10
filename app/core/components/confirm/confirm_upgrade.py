"""Confirm upgrade component

This component handles confirming member tier upgrade action.
Dashboard data is schema-validated at the state manager level.
Components can store their own data in component_data.data.
"""

from typing import Any, Dict

from core.error.types import ValidationResult

from ..confirm import ConfirmBase


class ConfirmUpgrade(ConfirmBase):
    """Handles member tier upgrade confirmation"""

    def __init__(self):
        super().__init__("confirm_upgrade")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing member data"""
        self.state_manager = state_manager

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle member tier upgrade confirmation"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "confirm_upgrade"}
            )

        # Get dashboard data from state
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": "confirm_upgrade"}
            )

        # Get member ID from dashboard
        member_id = dashboard.get("member", {}).get("memberID")
        if not member_id:
            return ValidationResult.failure(
                message="No member ID found in dashboard",
                field="member_id",
                details={"component": "confirm_upgrade"}
            )

        # Get active account ID from state
        active_account_id = self.state_manager.get("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"component": "confirm_upgrade"}
            )

        # Create confirmation result
        result = {
            "confirmed": True,
            "member_id": member_id,
            "account_id": active_account_id
        }

        # Update state with confirmation data
        self.update_state(result, ValidationResult.success(result))
        return ValidationResult.success(result)

    def get_rejection_message(self) -> str:
        """Get message for when upgrade is rejected"""
        return "Member tier upgrade cancelled"

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation data

        Note: Member data is in dashboard state, we just need
        confirmation details here.
        """
        return {
            "confirmed": True,
            "account_id": value["account_id"]
        }
