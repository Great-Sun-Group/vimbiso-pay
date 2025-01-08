"""Account dashboard component

This component handles displaying the account dashboard with proper validation.
Also handles initial state setup after login.
"""

from typing import Any, Dict

from core.messaging.formatters.formatters import AccountFormatters
from core.messaging.types import Message
from core.messaging.utils import get_recipient
from core.utils.error_types import ValidationResult

from ..base import DisplayComponent


class AccountDashboard(DisplayComponent):
    """Handles account dashboard display and initial state"""

    def __init__(self):
        super().__init__("account_dashboard")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing dashboard data"""
        self.state_manager = state_manager

    def validate_display(self, value: Any) -> ValidationResult:
        """Validate display and handle menu selection"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "account_dashboard"}
            )

        try:
            # Display Phase - First time through
            if not isinstance(value, dict) or "type" not in value:
                # Get and validate dashboard data
                dashboard = self.state_manager.get("dashboard")
                if not dashboard:
                    return ValidationResult.failure(
                        message="No dashboard data found",
                        field="dashboard",
                        details={"component": "account_dashboard"}
                    )

                # Get active account ID set by flow
                active_account_id = self.state_manager.get("active_account_id")
                if not active_account_id:
                    return ValidationResult.failure(
                        message="No active account set",
                        field="active_account",
                        details={"component": "account_dashboard"}
                    )

                # Find active account
                accounts = dashboard.get("accounts", [])
                active_account = next(
                    (acc for acc in accounts if acc.get("accountID") == active_account_id),
                    None
                )
                if not active_account:
                    return ValidationResult.failure(
                        message="Active account not found",
                        field="accounts",
                        details={"component": "account_dashboard"}
                    )

                # Format active account data for display
                formatted_data = {
                    "accountName": active_account.get("accountName", ""),
                    "accountHandle": active_account.get("accountHandle", ""),
                    "accountType": active_account.get("accountType", ""),
                    "defaultDenom": active_account.get("defaultDenom", "USD"),
                    "securedNetBalancesByDenom": active_account.get("balanceData", {}).get("securedNetBalancesByDenom", []),
                    "netCredexAssetsInDefaultDenom": active_account.get("balanceData", {}).get("netCredexAssetsInDefaultDenom", "0.00")
                }

                # Add tier limit if member data exists
                member = dashboard.get("member", {})
                if member and member.get("memberTier"):
                    formatted_data["tier_limit_raw"] = member.get("tierLimit", "0.00")

                # Get recipient for messages
                recipient = get_recipient(self.state_manager)

                # Send account info as text
                self.state_manager.messaging.send_text(
                    recipient=recipient,
                    text=self.to_message_content(formatted_data)
                )

                # Get interactive menu from WhatsApp formatter
                from core.messaging.formatters.whatsapp_menus import \
                    WhatsAppMenus
                menu = WhatsAppMenus.get_interactive_menu()

                # Send interactive menu using proper content type
                from core.messaging.types import (InteractiveContent,
                                                  InteractiveType)
                menu_content = InteractiveContent(
                    interactive_type=InteractiveType.LIST,
                    body=menu["body"]["text"],
                    sections=menu["action"]["sections"],
                    button_text=menu["action"]["button"]
                )
                self.state_manager.messaging.send_message(
                    Message(recipient=recipient, content=menu_content)
                )

                # Return success with await_input to stay active for input
                return ValidationResult.success(
                    formatted_data,
                    metadata={"await_input": True}  # Signal flow to wait for input
                )

            # Input Phase - When we get a response
            selection = value.get("text", "").strip()
            from core.messaging.formatters.whatsapp_menus import WhatsAppMenus
            if WhatsAppMenus.is_valid_option(selection):
                # Valid selection, return to progress
                return ValidationResult.success({"selection": selection})

            # Invalid selection, return failure but stay on component
            return ValidationResult.failure(
                message="Invalid selection. Please choose from the available options.",
                field="selection",
                details={"component": "account_dashboard"}
            )

        except Exception as e:
            return ValidationResult.failure(
                message=str(e),
                field="display",
                details={
                    "component": "account_dashboard",
                    "error": str(e)
                }
            )

    def to_message_content(self, value: Dict) -> str:
        """Convert dashboard data to message content using AccountFormatters"""
        return AccountFormatters.format_dashboard(value)
