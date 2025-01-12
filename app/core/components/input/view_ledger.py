"""View ledger component

This component handles displaying paginated ledger entries:
- Shows 7 rows per page
- Provides navigation buttons
- Handles pagination state
- Returns to dashboard on request
"""

import logging
from typing import Any, Dict, List

from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.messaging.types import Button
from core.components.base import InputComponent

logger = logging.getLogger(__name__)

# Ledger display templates
LEDGER_HEADER = """📊 *Account Ledger*

{account_name}
💳 {account_handle}

{entries}"""

LEDGER_ENTRY = """💰 {amount}
👤 {counterparty}
📝 {description}
⏰ {timestamp}
"""


class ViewLedger(InputComponent):
    """Handles ledger display and navigation"""

    def __init__(self):
        super().__init__("view_ledger")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate ledger display and handle navigation"""
        try:
            # Get current state
            current_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = current_data.get("incoming_message")

            # Initial activation - display first page
            if not current_data.get("awaiting_input"):
                return self._display_ledger(start_row=0)

            # Process button selection
            if not incoming_message:
                return ValidationResult.success(None)

            # Validate interactive message
            if incoming_message.get("type") != "interactive":
                return ValidationResult.failure(
                    message="Please use the navigation buttons",
                    field="type",
                    details={"message": incoming_message}
                )

            # Get button info
            text = incoming_message.get("text", {})
            if text.get("interactive_type") != "button":
                return ValidationResult.failure(
                    message="Please use the navigation buttons",
                    field="interactive_type",
                    details={"text": text}
                )

            # Handle button press
            button = text.get("button", {})
            button_id = button.get("id")

            logger.debug(f"Button ID: {button_id}")
            return self._handle_button(button_id)

        except Exception as e:
            logger.error(f"Error in view ledger: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="view_ledger",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def _display_ledger(self, start_row: int) -> ValidationResult:
        """Display ledger entries with navigation"""
        try:
            # Get account details
            dashboard = self.state_manager.get_state_value("dashboard", {})
            active_account_id = self.state_manager.get_state_value("active_account_id")
            if not active_account_id:
                return ValidationResult.failure(
                    message="No active account selected",
                    field="active_account",
                    details={"component": self.type}
                )

            account = next(
                (acc for acc in dashboard.get("accounts", [])
                 if acc.get("accountID") == active_account_id),
                None
            )
            if not account:
                return ValidationResult.failure(
                    message="Active account not found",
                    field="account",
                    details={"active_account_id": active_account_id}
                )

            # Store pagination state
            self.update_component_data(
                data={
                    "account_id": active_account_id,
                    "start_row": start_row,
                    "num_rows": 7  # Fixed to 7 rows per page
                },
                awaiting_input=False
            )

            # Signal API component to fetch data
            return ValidationResult.success({
                "fetch_ledger": True,
                "start_row": start_row
            })

        except Exception as e:
            logger.error(f"Error preparing ledger display: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="display",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def _handle_button(self, button_id: str) -> ValidationResult:
        """Handle navigation button press"""
        try:
            # Get current pagination state
            current_data = self.state_manager.get_state_value("component_data", {}).get("data", {})
            start_row = current_data.get("start_row", 0)

            # Handle different buttons
            if button_id == "next":
                # Move forward 7 rows
                return self._display_ledger(start_row + 7)

            if button_id == "prev":
                # Move back 7 rows, but not before 0
                return self._display_ledger(max(0, start_row - 7))

            if button_id == "dashboard":
                # Return to dashboard
                self.update_component_data(
                    data={},
                    awaiting_input=False,
                    component_result="send_dashboard"
                )
                return ValidationResult.success(None)

            return ValidationResult.failure(
                message="Invalid button selection",
                field="button",
                details={"button_id": button_id}
            )

        except Exception as e:
            logger.error(f"Error handling button: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="button",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def display_entries(self, entries: List[Dict], has_more: bool, account_name: str, account_handle: str) -> None:
        """Display ledger entries with navigation buttons"""
        try:
            # Format entries
            formatted_entries = []
            for entry in entries:
                formatted_entries.append(LEDGER_ENTRY.format(
                    amount=entry.get("formattedAmount", "Unknown"),
                    counterparty=entry.get("counterpartyAccountName", "Unknown"),
                    description=entry.get("description", ""),
                    timestamp=entry.get("timestamp", "Unknown")
                ))

            # Format complete message
            message = LEDGER_HEADER.format(
                account_name=account_name,
                account_handle=account_handle,
                entries="\n".join(formatted_entries) if formatted_entries else "No transactions found"
            )

            # Create navigation buttons
            buttons = []

            # Previous button if not at start
            current_data = self.state_manager.get_state_value("component_data", {}).get("data", {})
            if current_data.get("start_row", 0) > 0:
                buttons.append(Button(id="prev", title="⬅️ Previous"))

            # Next button if more entries available
            if has_more:
                buttons.append(Button(id="next", title="Next ➡️"))

            # Always show dashboard button
            buttons.append(Button(id="dashboard", title="🏠 Dashboard"))

            # Send message with buttons
            self.state_manager.messaging.send_interactive(
                body=message,
                buttons=buttons
            )
            self.set_awaiting_input(True)

        except Exception as e:
            logger.error(f"Error displaying entries: {str(e)}")
            raise ComponentException(
                message=f"Failed to display entries: {str(e)}",
                component=self.type,
                field="display",
                value=str(e)
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        if isinstance(value, dict) and value.get("fetch_ledger"):
            return {
                "fetch_ledger": True,
                "start_row": value.get("start_row", 0)
            }
        return {}
