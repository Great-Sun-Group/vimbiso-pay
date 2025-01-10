"""Display ledger section component

This component handles displaying a section of ledger entries.
"""

from typing import Any, Dict

from core.error.types import ValidationResult

from core.components.base import Component


class DisplayLedgerSection(Component):
    """Handles displaying a section of ledger entries"""

    def __init__(self):
        super().__init__("display_ledger_section")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing ledger data"""
        self.state_manager = state_manager

    def validate(self, value: Any) -> ValidationResult:
        """Validate and format ledger entries for display"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "display_ledger"}
            )

        # Get ledger data from state (components can store their own data in component_data.data)
        ledger_data = self.state_manager.get_state_value("component_data", {})
        if not ledger_data:
            return ValidationResult.failure(
                message="No ledger data found",
                field="component_data",
                details={"component": "display_ledger"}
            )
        entries = ledger_data.get("entries", [])
        if not entries:
            return ValidationResult.failure(
                message="No ledger entries found",
                field="entries",
                details={"component": "display_ledger"}
            )

        # Format entries for display
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                "date": entry.get("date"),
                "description": entry.get("description"),
                "amount": entry.get("amount"),
                "denom": entry.get("denom", "USD"),
                "type": entry.get("type", "transaction")
            })

        # Get pagination info
        total_pages = ledger_data.get("total_pages", 1)
        current_page = ledger_data.get("current_page", 1)

        return ValidationResult.success({
            "entries": formatted_entries,
            "total_pages": total_pages,
            "current_page": current_page
        })

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified display data"""
        return {
            "entries": value["entries"],
            "total_pages": value["total_pages"],
            "current_page": value["current_page"],
            "use_table": True  # Signal to use table format
        }
