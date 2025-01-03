"""Credex operation handlers using messaging service interface"""
import logging
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow

from .flows import OfferFlow, AcceptFlow

logger = logging.getLogger(__name__)


class CredexHandler:
    """Handler for credex-related operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service
        self.offer = OfferFlow(messaging_service)
        self.accept = AcceptFlow(messaging_service)

    def start_offer(self, state_manager: Any) -> Message:
        """Start offer flow"""
        try:
            # Initialize offer flow
            initialize_flow(state_manager, "credex_offer")

            # Send amount prompt
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text=self.offer.get_step_content("amount")
            )

        except Exception as e:
            logger.error("Failed to start offer flow", extra={"error": str(e)})
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="❌ Failed to start offer. Please try again."
            )

    def start_accept(self, state_manager: Any) -> Message:
        """Start accept flow"""
        try:
            # Initialize accept flow
            initialize_flow(state_manager, "credex_accept")

            # Get pending offers
            # TODO: Get from API
            pending_offers = []

            # Check if there are offers to accept
            if not pending_offers:
                return self.messaging.send_text(
                    recipient=MessageRecipient(
                        channel_id=state_manager.get_channel_id(),
                        member_id=state_manager.get("member_id")
                    ),
                    text="❌ No pending offers to accept."
                )

            # Format offer list
            offer_list = ["Pending offers:"]
            for offer in pending_offers:
                offer_list.append(
                    f"• {offer.get('amount')} from {offer.get('handle')}"
                )

            # Send selection prompt
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="\n".join([
                    self.accept.get_step_content("select"),
                    "",  # Empty line for spacing
                    "\n".join(offer_list)
                ])
            )

        except Exception as e:
            logger.error("Failed to start accept flow", extra={"error": str(e)})
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="❌ Failed to start accept. Please try again."
            )

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step"""
        try:
            if flow_type == "credex_offer":
                return self.offer.process_step(state_manager, step, input_value)
            elif flow_type == "credex_accept":
                return self.accept.process_step(state_manager, step, input_value)
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
