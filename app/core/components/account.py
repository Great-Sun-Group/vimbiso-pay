"""Account-related components

This module implements account-specific components with pure UI validation.
Business validation happens in services.

Components:
- AccountDashboard: Displays account overview and available actions
- AccountSelect: Handles account selection
- LedgerDisplay: Displays account ledger
"""
from typing import Any, Dict

from core.utils.error_types import ValidationResult

from .base import Component


class AccountDashboard(Component):
    """Account dashboard component showing overview and actions"""

    def __init__(self):
        super().__init__("dashboard")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing account data"""
        self.state_manager = state_manager

    def validate(self, value: Any) -> ValidationResult:
        """Validate account data with proper tracking"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "account_dashboard"}
            )

        # Get dashboard data - source of truth
        dashboard = self.state_manager.get("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"state": "missing_dashboard"}
            )

        # Get active account ID (local state)
        active_account_id = self.state_manager.get("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"state": "missing_active_account"}
            )

        # Find active account in dashboard accounts array
        dashboard_accounts = dashboard.get("accounts", [])  # Accounts array is directly in dashboard
        active_account = next(
            (acc for acc in dashboard_accounts if acc.get("accountID") == active_account_id),
            None
        )
        if not active_account:
            return ValidationResult.failure(
                message="Active account not found in dashboard",
                field="active_account",
                details={"account_id": active_account_id}
            )

        # Return dashboard (source of truth) and active account for convenience
        return ValidationResult.success({
            "dashboard": dashboard,
            "active_account": active_account  # Already validated to exist in accounts array
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified dashboard data with actions"""
        # Use the active account that validate() found
        dashboard_data = {
            "dashboard": value["dashboard"],
            "active_account": value["active_account"]
        }

        # Get pending offers counts
        dashboard = value["dashboard"]
        incoming_offers = len(dashboard.get("incomingOffers", []))
        outgoing_offers = len(dashboard.get("outgoingOffers", []))

        # Define sections with menu items
        sections = [
            {
                "title": "Credex Actions",
                "rows": [
                    {"id": "credex_offer", "title": "🔒 Offer Secured Credex", "description": "Create a new secured Credex offer"},
                    {"id": "credex_accept", "title": f"✅ Accept Credex ({incoming_offers})", "description": "Accept incoming Credex offers"},
                    {"id": "credex_decline", "title": f"❌ Decline Credex ({incoming_offers})", "description": "Decline incoming Credex offers"},
                    {"id": "credex_cancel", "title": f"🚫 Cancel Credex ({outgoing_offers})", "description": "Cancel your outgoing Credex offers"}
                ]
            },
            {
                "title": "Account Actions",
                "rows": [
                    {"id": "account_ledger", "title": "📊 View Account Ledger", "description": "See your account transaction history"}
                ]
            },
            {
                "title": "Member Actions",
                "rows": [
                    {"id": "member_upgrade", "title": "⭐ Upgrade Member Tier", "description": "Upgrade your membership level"}
                ]
            }
        ]

        # Return data with sections for list display
        return {
            **dashboard_data,
            "sections": sections,
            "use_list": True,  # Signal to use list format
            "button_text": "Action"  # Custom button text for list
        }


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
