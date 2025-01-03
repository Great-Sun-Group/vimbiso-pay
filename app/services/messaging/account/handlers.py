"""Account operation handlers using messaging service interface"""
import logging
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow

from .flows import LedgerFlow

logger = logging.getLogger(__name__)


class AccountHandler:
    """Handler for account-related operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service
        self.ledger = LedgerFlow(messaging_service)

    def start_ledger(self, state_manager: Any) -> Message:
        """Start ledger flow"""
        try:
            # Initialize ledger flow
            initialize_flow(state_manager, "account_ledger")

            # Get available accounts
            accounts = state_manager.get("accounts", [])
            if not accounts:
                return self.messaging.send_text(
                    recipient=MessageRecipient(
                        channel_id=state_manager.get_channel_id(),
                        member_id=state_manager.get("member_id")
                    ),
                    text="❌ No accounts available."
                )

            # Format account list
            account_list = ["Available accounts:"]
            for account in accounts:
                account_list.append(
                    f"• {account.get('accountName')} ({account.get('accountHandle')})"
                )

            # Send account selection prompt
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="\n".join([
                    self.ledger.get_step_content("select"),
                    "",  # Empty line for spacing
                    "\n".join(account_list)
                ])
            )

        except Exception as e:
            logger.error("Failed to start ledger flow", extra={"error": str(e)})
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="❌ Failed to start ledger view. Please try again."
            )

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step"""
        try:
            if flow_type == "account_ledger":
                return self.ledger.process_step(state_manager, step, input_value)
            else:
                raise FlowException(
                    message=f"Invalid flow type: {flow_type}",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

        except FlowException as e:
            # Handle flow errors
            logger.error(f"{flow_type} flow error", extra={
                "step": e.step,
                "action": e.action,
                "data": e.data
            })
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text=f"❌ {str(e)}"
            )

        except SystemException as e:
            # Handle system errors
            logger.error(f"{flow_type} system error", extra={
                "code": e.code,
                "service": e.service,
                "action": e.action
            })
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text=f"❌ {flow_type.replace('_', ' ').title()} failed. Please try again later."
            )

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected {flow_type} error", extra={
                "error": str(e),
                "step": step
            })
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="❌ An unexpected error occurred. Please try again."
            )
