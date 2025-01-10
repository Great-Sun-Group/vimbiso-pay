"""View ledger component

This component handles displaying the ledger view with proper validation.
"""

from typing import Any, Dict

from core.error.types import ValidationResult

from ..base import DisplayComponent


class ViewLedger(DisplayComponent):
    """Handles ledger view display"""

    def __init__(self):
        super().__init__("view_ledger")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing ledger data"""
        self.state_manager = state_manager

    def validate_display(self, value: Any) -> ValidationResult:
        """Validate and format ledger data for display"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "view_ledger"}
            )

        # Get active account from state
        active_account_id = self.state_manager.get("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"component": "view_ledger"}
            )

        # Get dashboard data from state
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": "view_ledger"}
            )

        # Find active account in dashboard
        accounts = dashboard.get("accounts", [])
        active_account = next(
            (acc for acc in accounts if acc.get("accountID") == active_account_id),
            None
        )
        if not active_account:
            return ValidationResult.failure(
                message="Active account not found in dashboard",
                field="active_account",
                details={"account_id": active_account_id}
            )

        # Format account data for display
        account_data = {
            "account_id": active_account_id,
            "account_name": active_account.get("accountName"),
            "balance": active_account.get("formattedBalance"),
            "denom": active_account.get("denom", "USD")
        }

        return ValidationResult.success({
            "title": "Account Ledger",
            "account": account_data
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified display data"""
        return {
            "title": value["title"],
            "account": value["account"],
            "use_section": True  # Signal to use section format
        }
