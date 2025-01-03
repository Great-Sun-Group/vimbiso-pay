"""Member operation handlers using messaging service interface"""
import logging
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow

from .flows import RegistrationFlow, UpgradeFlow

logger = logging.getLogger(__name__)


class MemberHandler:
    """Handler for member-related operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service
        self.registration = RegistrationFlow(messaging_service)
        self.upgrade = UpgradeFlow(messaging_service)

    def start_registration(self, state_manager: Any) -> Message:
        """Start registration flow"""
        try:
            # Initialize registration flow
            initialize_flow(state_manager, "registration")

            # Send welcome message
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text=self.registration.get_step_content("welcome")
            )

        except Exception as e:
            logger.error("Failed to start registration", extra={"error": str(e)})
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="❌ Failed to start registration. Please try again."
            )

    def start_upgrade(self, state_manager: Any) -> Message:
        """Start upgrade flow"""
        try:
            # Initialize upgrade flow
            initialize_flow(state_manager, "upgrade")

            # Send confirmation message
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text=self.upgrade.get_step_content("confirm")
            )

        except Exception as e:
            logger.error("Failed to start upgrade", extra={"error": str(e)})
            return self.messaging.send_text(
                recipient=MessageRecipient(
                    channel_id=state_manager.get_channel_id(),
                    member_id=state_manager.get("member_id")
                ),
                text="❌ Failed to start upgrade. Please try again."
            )

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step"""
        try:
            if flow_type == "registration":
                return self.registration.process_step(state_manager, step, input_value)
            elif flow_type == "upgrade":
                return self.upgrade.process_step(state_manager, step, input_value)
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
                text=f"❌ {flow_type.title()} failed. Please try again later."
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
