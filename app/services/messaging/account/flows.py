"""Account flows using messaging service interface"""
import logging
from typing import Any, Dict, Optional

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message
from core.utils.exceptions import FlowException, SystemException
from core.messaging.registry import FlowRegistry

from ..utils import get_recipient

logger = logging.getLogger(__name__)


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

        except FlowException:
            # Let flow errors propagate up
            raise

        except Exception as e:
            # Wrap other errors
            raise SystemException(
                message=str(e),
                code="FLOW_ERROR",
                service="account_flow",
                action=f"process_{step}"
            )
