"""Account dashboard component

This component handles displaying the account dashboard with proper validation.
Also handles initial state setup after login.
"""

from typing import Any, Dict

from core.messaging.types import Message
from core.messaging.utils import get_recipient
from core.error.types import ValidationResult
from core.error.exceptions import ComponentException

from ..base import DisplayComponent


class AccountDashboard(DisplayComponent):
    """Handles account dashboard display and initial state"""

    def __init__(self):
        super().__init__("account_dashboard")

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
                dashboard = self.state_manager.get_state_value("dashboard")
                if not dashboard:
                    return ValidationResult.failure(
                        message="No dashboard data found",
                        field="dashboard",
                        details={"component": "account_dashboard"}
                    )

                # Get active account ID set by flow
                active_account_id = self.state_manager.get_state_value("active_account_id")
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

                # Format header data
                account = active_account.get("accountName", "")
                handle = active_account.get("accountHandle", "")

                # Format secured balances
                secured_balances = active_account.get("balanceData", {}).get("securedNetBalancesByDenom", [])
                secured_balances_str = "\n".join(secured_balances) if secured_balances else "0.00 USD"

                # Format net assets
                try:
                    net_value = float(active_account.get("balanceData", {}).get("netCredexAssetsInDefaultDenom", "0.00"))
                    denom = active_account.get("defaultDenom", "USD")
                    net_assets = f"  {net_value:.2f} {denom}"
                except (ValueError, TypeError):
                    net_assets = f"  0.00 {active_account.get('defaultDenom', 'USD')}"

                # Format tier limit display
                member = dashboard.get("member", {})
                tier_limit_display = ""
                if member and member.get("memberTier", 0) < 3:
                    try:
                        amount_remaining = float(member.get("amountRemainingUSD", "0.00"))
                        tier_limit_display = f"\n\n⏳ DAILY MEMBER TIER LIMIT: {amount_remaining:.2f} USD"
                    except (ValueError, TypeError):
                        tier_limit_display = "\n\n⏳ DAILY MEMBER TIER LIMIT: 0.00 USD"

                # Format final display data
                formatted_data = {
                    "account": account,
                    "handle": handle,
                    "secured_balances": secured_balances_str,
                    "net_assets": net_assets,
                    "tier_limit_display": tier_limit_display
                }

                # Get recipient for messages
                recipient = get_recipient(self.state_manager)

                # Get account info text
                account_info = self.to_message_content(formatted_data)

                # Create menu options aligned with flow paths
                from core.messaging.types import (InteractiveContent,
                                                  InteractiveType,
                                                  Section)

                # Define menu options matching headquarters.py flow paths
                menu_options = [
                    {"id": "offer_secured", "title": "Create Offer"},
                    {"id": "accept_offer", "title": "Accept Offer"},
                    {"id": "decline_offer", "title": "Decline Offer"},
                    {"id": "cancel_offer", "title": "Cancel Offer"},
                    {"id": "view_ledger", "title": "View Ledger"},
                    {"id": "upgrade_membertier", "title": "Upgrade Tier"}
                ]

                # Create menu content
                menu_content = InteractiveContent(
                    interactive_type=InteractiveType.LIST,
                    body=account_info,
                    sections=[
                        Section(
                            title="Account Actions",
                            rows=menu_options
                        )
                    ],
                    button_text="Select Action"
                )
                try:
                    # Set component to await input before sending menu
                    self.set_awaiting_input(True)

                    self.state_manager.messaging.send_message(
                        Message(recipient=recipient, content=menu_content)
                    )

                    return ValidationResult.success(formatted_data)
                except Exception as e:
                    raise ComponentException(
                        message=f"Failed to send menu message: {str(e)}",
                        component=self.type,
                        field="messaging",
                        value=str(menu_content),
                        validation=self.validation_state
                    )

            # Input Phase - When we get a response
            from core.messaging.menus import WhatsAppMenus
            component_data = self.state_manager.get_state_value("component_data", {})
            message = component_data.get("message", {})

            # For interactive messages, extract selection ID
            if (message.get("type") == "interactive" and
               WhatsAppMenus.is_valid_option(message)):
                interactive = message.get("interactive", {})
                if interactive.get("type") == "list_reply":
                    selection = interactive.get("list_reply", {}).get("id")
                    if selection:
                        # Validate selection matches expected flow paths
                        valid_paths = [
                            "offer_secured",
                            "accept_offer",
                            "decline_offer",
                            "cancel_offer",
                            "view_ledger",
                            "upgrade_membertier"
                        ]

                        if selection in valid_paths:
                            # Set result and release flow
                            self.update_component_state(
                                component_result=selection,
                                awaiting_input=False
                            )
                            return ValidationResult.success(True)

            # Invalid selection, return failure but stay on component
            return ValidationResult.failure(
                message="Invalid selection. Please choose from the available options.",
                field="selection",
                details={"component": self.type}
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
        """Format dashboard data using template"""
        from core.messaging.messages import ACCOUNT_DASHBOARD
        return ACCOUNT_DASHBOARD.format(**value)
