"""Account dashboard component

This component handles displaying the account dashboard with proper validation.
Also handles initial state setup after login.
"""

from typing import Any

from core.components.base import InputComponent
from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.messaging.types import InteractiveType, MessageType, Section

# Account template
ACCOUNT_DASHBOARD = """💳 *{account}*
{handle}

*💰 Secured Balances*
{secured_balances}

*📊 Net Assets*
{net_assets}{tier_limit_display}"""


class AccountDashboard(InputComponent):
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
            # Display Phase - When not awaiting input
            if not self.state_manager.is_awaiting_input():
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

                # Get account info text
                account_info = ACCOUNT_DASHBOARD.format(**formatted_data)

                # Get pending counts from active account
                pending_in = len([
                    o for o in active_account.get("offers", [])
                    if o.get("status") == "pending" and o.get("type") == "incoming"
                ])
                pending_out = len([
                    o for o in active_account.get("offers", [])
                    if o.get("status") == "pending" and o.get("type") == "outgoing"
                ])

                # Format pending counts
                pending_in_formatted = f" ({pending_in})" if pending_in > 0 else ""
                pending_out_formatted = f" ({pending_out})" if pending_out > 0 else ""

                # Define menu options with emojis and counts
                menu_options = []

                # Credex Actions
                menu_options.append({"id": "offer_secured", "title": "Offer secured credex", "description": "💸 Offer secured credex"})
                if pending_in > 0:
                    menu_options.append({"id": "accept_offers_bulk", "title": "Accept all pending offers", "description": f"✅ Accept all pending offers{pending_in_formatted}"})
                    menu_options.append({"id": "accept_offer", "title": "Accept a pending offer", "description": f"✅ Accept a pending offer{pending_in_formatted}"})
                    menu_options.append({"id": "decline_offer", "title": "Decline a pending offer", "description": f"❌ Decline a pending offer{pending_in_formatted}"})
                if pending_out > 0:
                    menu_options.append({"id": "cancel_offer", "title": "Cancel your offer", "description": f"🚫 Cancel your offer{pending_out_formatted}"})

                # Account Actions
                menu_options.append({"id": "view_ledger", "title": "View account ledger", "description": "📊 View account ledger"})

                # Member Actions - only show upgrade option for tier 1
                if member.get("memberTier") == 1:
                    menu_options.append({"id": "upgrade_membertier", "title": "Upgrade your member tier", "description": "⭐ Upgrade your member tier"})

                try:
                    # Set component to await input before sending menu
                    self.set_awaiting_input(True)

                    # Pass properly structured menu data to messaging service
                    self.state_manager.messaging.send_interactive(
                        body=account_info,
                        sections=[Section(
                            title="Actions",
                            rows=menu_options
                        )],
                        button_text="🕹️ Select Action"
                    )

                    return ValidationResult.success(formatted_data)
                except Exception as e:
                    raise ComponentException(
                        message=f"Failed to send menu message: {str(e)}",
                        component=self.type,
                        field="messaging",
                        value=str(account_info),
                        validation=self.validation_state
                    )

            # Input Phase - When we get a response
            component_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = component_data.get("incoming_message", {})

            # For interactive messages, extract selection ID
            if incoming_message.get("type") == MessageType.INTERACTIVE.value:
                text = incoming_message.get("text", {})
                if text.get("interactive_type") == InteractiveType.LIST.value:
                    selection = text.get("list_reply", {}).get("id")
                    if selection:
                        # Validate selection matches expected flow paths
                        valid_paths = [
                            "offer_secured",
                            "accept_offers_bulk",
                            "accept_offer",
                            "decline_offer",
                            "cancel_offer",
                            "view_ledger",
                            "upgrade_membertier"
                        ]
                        if selection in valid_paths:
                            # Set result and release flow
                            self.update_component_data(
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
