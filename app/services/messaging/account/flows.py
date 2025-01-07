"""Account flows using messaging service interface"""
import logging
from typing import Any, Dict, Optional

from core.components.registry import create_component
from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import Message
from core.utils.exceptions import FlowException, SystemException

from ..utils import get_recipient

logger = logging.getLogger(__name__)


class AccountDashboardFlow:
    """Account dashboard flow"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get dashboard step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("account_dashboard", step)
        return ""  # No content needed - component handles display

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process dashboard step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("account_dashboard", step)
            recipient = get_recipient(state_manager)

            if step == "display":
                # Get dashboard component
                component_type = FlowRegistry.get_step_component("account_dashboard", step)
                component = create_component(component_type)

                # Set state manager for account access
                component.set_state_manager(state_manager)

                # Validate and get dashboard data
                validation_result = component.validate({})
                if not validation_result.valid:
                    raise FlowException(
                        message=validation_result.error["message"],
                        step="display",  # Explicit step name
                        action="validate_dashboard",  # More specific action
                        data={
                            "validation_error": validation_result.error,
                            "component": "account_dashboard"
                        }
                    )

                # Get verified dashboard data with actions
                verified_data = component.to_verified_data(validation_result.value)

                # Format message using account data
                from core.messaging.formatters import AccountFormatters
                from core.messaging.types import Button

                # Get account data and merge with balance data
                active_account = verified_data["active_account"]
                balance_data = active_account.get("balanceData", {})

                # Get member tier from dashboard data (source of truth)
                member_data = verified_data["dashboard"].get("member", {})
                member_tier = member_data.get("memberTier")
                account_data = {
                    "accountName": active_account.get("accountName"),
                    "accountHandle": active_account.get("accountHandle"),
                    "netCredexAssetsInDefaultDenom": balance_data.get('netCredexAssetsInDefaultDenom', '0.00'),
                    "defaultDenom": member_data.get('defaultDenom', 'USD'),
                    **balance_data
                }

                # Only include tier limit for tier < 2
                if member_tier < 2:
                    account_data["tier_limit_raw"] = member_data.get("remainingAvailableUSD", "0.00")
                message = AccountFormatters.format_dashboard(account_data)

                # Convert button dictionaries to Button objects (max 3 for WhatsApp)
                buttons = [
                    Button(id=btn["id"], title=btn["title"])
                    for btn in verified_data["buttons"][:3]  # Limit to first 3 buttons
                ]

                # Create interactive message with buttons
                return messaging_service.send_interactive(
                    recipient=recipient,
                    body=message,
                    buttons=buttons
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException as e:
            # Ensure all required attributes are present
            if not hasattr(e, 'step'):
                e.step = step
            if not hasattr(e, 'action'):
                e.action = 'validate'
            if not hasattr(e, 'data'):
                e.data = {}
            raise e

        except Exception as e:
            raise SystemException(
                message=str(e),
                code="FLOW_ERROR",
                service="account_flow",
                action=f"process_{step}"
            )


class LedgerFlow:
    """Account ledger flow"""

    @staticmethod
    def get_step_content(step: str, data: Optional[Dict] = None) -> str:
        """Get ledger step content"""
        # Validate step through registry
        FlowRegistry.validate_flow_step("account_ledger", step)

        if step == "select":
            return (
                "📊 View Account Ledger\n"
                "Please select an account to view:"
            )
        elif step == "display":
            if not data:
                return "No ledger data available."

            # Format ledger data
            entries = data.get("entries", [])
            if not entries:
                return "No recent transactions."

            result = ["Recent Transactions:"]
            for entry in entries[:5]:  # Show last 5 transactions
                result.append(
                    f"• {entry.get('date')}: {entry.get('description')}\n"
                    f"  Amount: {entry.get('amount')} {entry.get('denom')}"
                )
            return "\n".join(result)
        return ""

    @staticmethod
    def process_step(messaging_service: MessagingServiceInterface, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process ledger step"""
        try:
            # Validate step through registry
            FlowRegistry.validate_flow_step("account_ledger", step)
            recipient = get_recipient(state_manager)

            if step == "select":
                # Validate account selection
                if not isinstance(input_value, str):
                    raise FlowException(
                        message="Invalid account selection",
                        step=step,
                        action="validate",
                        data={"value": input_value}
                    )

                # Update state with selection
                state_manager.update_state({
                    "flow_data": {
                        "data": {"account_id": input_value}
                    }
                })

                # TODO: Fetch ledger data from API
                ledger_data = {"entries": []}  # Placeholder

                # Send ledger display
                return messaging_service.send_text(
                    recipient=recipient,
                    text=LedgerFlow.get_step_content("display", ledger_data)
                )

            else:
                raise FlowException(
                    message=f"Invalid step: {step}",
                    step=step,
                    action="validate",
                    data={"value": input_value}
                )

        except FlowException as e:
            # Ensure all required attributes are present
            if not hasattr(e, 'step'):
                e.step = step
            if not hasattr(e, 'action'):
                e.action = 'validate'
            if not hasattr(e, 'data'):
                e.data = {}
            raise e

        except Exception as e:
            # Wrap other errors
            raise SystemException(
                message=str(e),
                code="FLOW_ERROR",
                service="account_flow",
                action=f"process_{step}"
            )
