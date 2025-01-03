"""Credex operation handlers using clean architecture patterns

Handlers coordinate between flows and services, managing state progression.
"""

import logging
from datetime import datetime
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow
from core.utils.error_handler import ErrorHandler
from services.credex.service import get_credex_service

from .flows import OfferFlow, ActionFlow
from ..utils import get_recipient

logger = logging.getLogger(__name__)


class CredexHandler:
    """Handler for credex-related operations with proper flow management"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service

    def start_offer(self, state_manager: Any) -> Message:
        """Start offer flow with proper state initialization"""
        try:
            # Initialize flow with proper structure
            initialize_flow(
                state_manager=state_manager,
                flow_type="credex_offer",
                initial_data={
                    "offer_type": "new",
                    "created_at": datetime.utcnow().isoformat()
                }
            )

            # Get recipient for messaging
            recipient = get_recipient(state_manager)

            # Get step content with progress
            flow_state = state_manager.get_flow_state()
            step_content = OfferFlow.get_step_content("amount")
            progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"

            # Send prompt with progress
            return self.messaging.send_text(
                recipient=recipient,
                text=f"{step_content}\n\n{progress}"
            )

        except Exception as e:
            # Use enhanced error handling
            logger.error("Failed to start offer flow", extra={
                "error": str(e),
                "handler": "credex",
                "action": "start_offer"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="credex",
                action="start_offer",
                message="Failed to start offer flow",
                error=e
            )

            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def _start_action_flow(self, state_manager: Any, action_type: str) -> Message:
        """Start action flow (accept/decline/cancel) with proper state initialization"""
        try:
            # Get pending offers first
            credex_service = get_credex_service(state_manager)
            success, result = credex_service["get_credex"]("pending")

            # Handle no offers early
            if not success or not result.get("offers"):
                error_response = ErrorHandler.handle_flow_error(
                    step="start",
                    action="get_offers",
                    data={},
                    message=f"No pending offers to {action_type}"
                )
                return self.messaging.send_text(
                    recipient=get_recipient(state_manager),
                    text=f"❌ {error_response['error']['message']}"
                )

            # Format offers
            offers = result["offers"]
            offer_list = ["Pending offers:"]
            for offer in offers:
                offer_list.append(
                    f"• {offer.get('amount')} from {offer.get('handle')}"
                )

            # Initialize flow with offers data
            initialize_flow(
                state_manager=state_manager,
                flow_type=f"credex_{action_type}",
                initial_data={
                    "pending_offers": offers,
                    "started_at": datetime.utcnow().isoformat()
                }
            )

            # Get recipient and flow state
            recipient = get_recipient(state_manager)
            flow_state = state_manager.get_flow_state()

            # Build message with progress
            step_content = ActionFlow.get_step_content(f"credex_{action_type}", "select")
            progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"
            message = "\n".join([
                step_content,
                "",  # Empty line for spacing
                "\n".join(offer_list),
                "",  # Empty line for spacing
                progress
            ])

            return self.messaging.send_text(
                recipient=recipient,
                text=message
            )

        except Exception as e:
            # Use enhanced error handling
            logger.error(f"Failed to start {action_type} flow", extra={
                "error": str(e),
                "handler": "credex",
                "action": f"start_{action_type}"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="credex",
                action=f"start_{action_type}",
                message=f"Failed to start {action_type} flow",
                error=e
            )

            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def start_accept(self, state_manager: Any) -> Message:
        """Start accept flow with proper state initialization"""
        return self._start_action_flow(state_manager, "accept")

    def start_decline(self, state_manager: Any) -> Message:
        """Start decline flow with proper state initialization"""
        return self._start_action_flow(state_manager, "decline")

    def start_cancel(self, state_manager: Any) -> Message:
        """Start cancel flow with proper state initialization"""
        return self._start_action_flow(state_manager, "cancel")

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step with proper error boundaries"""
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
            if flow_type == "credex_offer":
                result = OfferFlow.process_step(self.messaging, state_manager, step, input_value)
            elif flow_type.startswith("credex_"):
                # Extract action type from flow type (e.g. "credex_accept" -> "accept")
                action_type = flow_type.split("_", 1)[1]
                if action_type not in {"accept", "decline", "cancel"}:
                    raise FlowException(
                        message=f"Invalid flow type: {flow_type}",
                        step=step,
                        action="handle_flow",
                        data={"flow_type": flow_type}
                    )
                result = ActionFlow.process_step(self.messaging, state_manager, step, input_value, flow_type)
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
                if flow_state and "message" in result:
                    # Add progress to message
                    progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"
                    result["message"] = f"{result['message']}\n\n{progress}"

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
                code=e.code,
                service=e.service,
                action=e.action,
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
                service="credex",
                action="handle_flow",
                message=f"Unexpected error in {flow_type} flow",
                error=e
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )
