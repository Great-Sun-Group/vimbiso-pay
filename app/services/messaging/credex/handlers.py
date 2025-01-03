"""Credex operation handlers using clean architecture patterns

Handlers coordinate between flows and services, managing state progression.
"""

import logging
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow
from services.credex.service import get_credex_service

from .flows import OfferFlow, AcceptFlow

logger = logging.getLogger(__name__)


class CredexHandler:
    """Handler for credex-related operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service
        self.offer = OfferFlow(messaging_service)
        self.accept = AcceptFlow(messaging_service)

    def start_offer(self, state_manager: Any) -> Message:
        """Start offer flow with proper state initialization"""
        try:
            # Initialize flow with step index and component state
            initialize_flow(state_manager, "credex_offer")
            state_manager.update_state({
                "flow_data": {
                    "step_index": 0,
                    "active_component": {
                        "type": "amount_input",
                        "value": None,
                        "validation": {
                            "in_progress": False,
                            "error": None
                        }
                    }
                }
            })

            # Send amount prompt
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=self.offer.get_step_content("amount")
            )

        except Exception as e:
            logger.error("Failed to start offer flow", extra={"error": str(e)})
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="❌ Failed to start offer. Please try again."
            )

    def start_accept(self, state_manager: Any) -> Message:
        """Start accept flow with proper state initialization"""
        try:
            # Initialize flow with step index and component state
            initialize_flow(state_manager, "credex_accept")
            state_manager.update_state({
                "flow_data": {
                    "step_index": 0,
                    "active_component": {
                        "type": "select_input",
                        "value": None,
                        "validation": {
                            "in_progress": False,
                            "error": None
                        }
                    }
                }
            })

            # Get pending offers through service
            credex_service = get_credex_service(state_manager)
            success, result = credex_service["get_credex"]("pending")

            # Handle no offers
            if not success or not result.get("offers"):
                return self.messaging.send_text(
                    recipient=self._get_recipient(state_manager),
                    text="❌ No pending offers to accept."
                )

            # Format offer list
            offers = result["offers"]
            offer_list = ["Pending offers:"]
            for offer in offers:
                offer_list.append(
                    f"• {offer.get('amount')} from {offer.get('handle')}"
                )

            # Update state with offers
            state_manager.update_state({
                "flow_data": {
                    "data": {
                        "pending_offers": offers
                    }
                }
            })

            # Send selection prompt
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="\n".join([
                    self.accept.get_step_content("select"),
                    "",  # Empty line for spacing
                    "\n".join(offer_list)
                ])
            )

        except Exception as e:
            logger.error("Failed to start accept flow", extra={"error": str(e)})
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="❌ Failed to start accept. Please try again."
            )

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step with proper error boundaries"""
        try:
            # Validate flow type
            if flow_type == "credex_offer":
                result = self.offer.process_step(state_manager, step, input_value)
            elif flow_type == "credex_accept":
                result = self.accept.process_step(state_manager, step, input_value)
            else:
                raise FlowException(
                    message=f"Invalid flow type: {flow_type}",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

            # Increment step index on success
            if not isinstance(result, FlowException):
                current_index = state_manager.get_flow_state().get("step_index", 0)
                state_manager.update_state({
                    "flow_data": {
                        "step_index": current_index + 1
                    }
                })

            return result

        except FlowException as e:
            # Handle flow errors (validation, business logic)
            logger.error(f"{flow_type} flow error", extra={
                "step": e.step,
                "action": e.action,
                "data": e.data
            })
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {str(e)}"
            )

        except SystemException as e:
            # Handle system errors (API, infrastructure)
            logger.error(f"{flow_type} system error", extra={
                "code": e.code,
                "service": e.service,
                "action": e.action
            })
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {flow_type.replace('_', ' ').title()} failed. Please try again later."
            )

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected {flow_type} error", extra={
                "error": str(e),
                "step": step
            })
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="❌ An unexpected error occurred. Please try again."
            )

    def _get_recipient(self, state_manager: Any) -> MessageRecipient:
        """Get message recipient from state"""
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=state_manager.get("member_id")
        )
