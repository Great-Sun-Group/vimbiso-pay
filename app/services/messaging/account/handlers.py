"""Account operation handlers using clean architecture patterns

Handlers coordinate between flows and services, managing state progression.
"""

import logging
from datetime import datetime
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import (
    InteractiveContent,
    Message,
    TextContent,
)
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow
from core.utils.error_handler import ErrorHandler

from .flows import AccountDashboardFlow, LedgerFlow
from ..utils import get_recipient

logger = logging.getLogger(__name__)


class AccountHandler:
    """Handler for account-related operations with proper state management"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service

    def start_dashboard(self, state_manager: Any) -> Message:
        """Start dashboard flow with proper state initialization"""
        try:
            try:
                # Initialize flow
                initialize_flow(
                    state_manager=state_manager,
                    flow_type="account_dashboard",
                    initial_data={
                        "started_at": datetime.utcnow().isoformat()
                    }
                )

                # Process initial display step
                return self.handle_flow_step(
                    state_manager=state_manager,
                    flow_type="account_dashboard",
                    step="display",
                    input_value={}
                )
            except FlowException as e:
                # Ensure flow exception has required attributes
                if not hasattr(e, 'step'):
                    e.step = "display"
                if not hasattr(e, 'action'):
                    e.action = "initialize"
                if not hasattr(e, 'data'):
                    e.data = {}
                raise e

        except FlowException as e:
            # Enhanced flow error handling
            error_response = ErrorHandler.handle_flow_error(
                step=e.step,
                action=e.action,
                data=e.data,
                message=str(e),
                flow_state=state_manager.get_flow_state()
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except Exception as e:
            # Enhanced system error handling
            logger.error("Failed to start dashboard", extra={
                "error": str(e),
                "handler": "account",
                "action": "start_dashboard"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="account",
                action="start_dashboard",
                message="Failed to start dashboard view",
                error=e
            )

            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def start_ledger(self, state_manager: Any) -> Message:
        """Start ledger flow with proper state initialization"""
        try:
            # Get available accounts first
            accounts = state_manager.get("accounts", [])
            if not accounts:
                error_response = ErrorHandler.handle_flow_error(
                    step="start",
                    action="get_accounts",
                    data={},
                    message="No accounts available"
                )
                return self.messaging.send_text(
                    recipient=get_recipient(state_manager),
                    text=f"❌ {error_response['error']['message']}"
                )

            # Format account list
            account_list = ["Available accounts:"]
            for account in accounts:
                account_list.append(
                    f"• {account.get('accountName')} ({account.get('accountHandle')})"
                )

            try:
                # Initialize flow with accounts data
                initialize_flow(
                    state_manager=state_manager,
                    flow_type="account_ledger",
                    initial_data={
                        "available_accounts": accounts,
                        "started_at": datetime.utcnow().isoformat()
                    }
                )

                # Get recipient and flow state
                recipient = get_recipient(state_manager)
                flow_state = state_manager.get_flow_state()
            except FlowException as e:
                # Ensure flow exception has required attributes
                if not hasattr(e, 'step'):
                    e.step = "select"
                if not hasattr(e, 'action'):
                    e.action = "initialize"
                if not hasattr(e, 'data'):
                    e.data = {}
                raise e

            # Build message with progress
            step_content = LedgerFlow.get_step_content("select")
            progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"
            message = "\n".join([
                step_content,
                "",  # Empty line for spacing
                "\n".join(account_list),
                "",  # Empty line for spacing
                progress
            ])

            return self.messaging.send_text(
                recipient=recipient,
                text=message
            )

        except FlowException as e:
            # Enhanced flow error handling
            error_response = ErrorHandler.handle_flow_error(
                step=e.step,
                action=e.action,
                data=e.data,
                message=str(e),
                flow_state=state_manager.get_flow_state()
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except Exception as e:
            # Enhanced system error handling
            logger.error("Failed to start ledger flow", extra={
                "error": str(e),
                "handler": "account",
                "action": "start_ledger"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="account",
                action="start_ledger",
                message="Failed to start ledger view",
                error=e
            )

            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step with proper error boundaries"""
        # Initialize flow_state outside try block
        flow_state = None
        try:
            # Get flow state for context
            flow_state = state_manager.get_flow_state()
            if not flow_state:
                raise FlowException(
                    message="No active flow",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

            # Process step through appropriate flow class
            if flow_type == "account_dashboard":
                result = AccountDashboardFlow.process_step(self.messaging, state_manager, step, input_value)
            elif flow_type == "account_ledger":
                result = LedgerFlow.process_step(self.messaging, state_manager, step, input_value)
            else:
                raise FlowException(
                    message=f"Invalid flow type: {flow_type}",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

            # Handle success with progress
            if not isinstance(result, FlowException):
                # Get updated flow state
                flow_state = state_manager.get_flow_state()
                if flow_state and isinstance(result, Message):
                    # Create new message with progress
                    progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"
                    recipient = get_recipient(state_manager)

                    # For text messages, append progress
                    if isinstance(result.content, TextContent):
                        return self.messaging.send_text(
                            recipient=recipient,
                            text=f"{result.content.body}\n\n{progress}"
                        )
                    # For interactive messages, keep original format
                    elif isinstance(result.content, InteractiveContent):
                        return result

            return result

        except FlowException as e:
            # Enhanced flow error handling
            error_response = ErrorHandler.handle_flow_error(
                step=e.step,
                action=e.action,
                data=e.data,
                message=str(e),
                flow_state=flow_state
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except SystemException as e:
            # Enhanced system error handling
            error_response = ErrorHandler.handle_system_error(
                code="SYSTEM_ERROR",
                service="account",
                action="handle_flow",
                message=str(e),
                error=e
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except Exception as e:
            # Enhanced unexpected error handling
            error_response = ErrorHandler.handle_system_error(
                code="UNEXPECTED_ERROR",
                service="account",
                action="handle_flow",
                message=f"Unexpected error in {flow_type} flow",
                error=e
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )
