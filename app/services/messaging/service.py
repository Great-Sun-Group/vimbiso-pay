"""Channel-agnostic messaging service"""
import logging
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.messaging.registry import FlowRegistry

from .member.handlers import MemberHandler
from .member.auth import AuthHandler
from .account.handlers import AccountHandler
from .credex.handlers import CredexHandler

logger = logging.getLogger(__name__)


class MessagingService:
    """Coordinates messaging operations across channels"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        """Initialize with channel-specific messaging service"""
        self.messaging = messaging_service
        self.member = MemberHandler(messaging_service)
        self.auth = AuthHandler(messaging_service)
        self.account = AccountHandler(messaging_service)
        self.credex = CredexHandler(messaging_service)

    def _get_recipient(self, state_manager: Any) -> MessageRecipient:
        """Get message recipient from state"""
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=state_manager.get("member_id")
        )

    def handle_message(self, state_manager: Any, message_type: str, message_text: str) -> Message:
        """Handle incoming message using appropriate handler"""
        try:
            # Check if we're in a flow
            flow_data = state_manager.get("flow_data")
            if flow_data:
                flow_type = flow_data.get("flow_type")
                current_step = flow_data.get("step")

                # Get flow config to determine handler
                config = FlowRegistry.get_flow_config(flow_type)
                handler_type = config.get("handler_type", "member")

                # Route to appropriate handler
                if handler_type == "member":
                    return self.member.handle_flow_step(
                        state_manager,
                        flow_type,
                        current_step,
                        message_text
                    )
                elif handler_type == "account":
                    return self.account.handle_flow_step(
                        state_manager,
                        flow_type,
                        current_step,
                        message_text
                    )
                elif handler_type == "credex":
                    return self.credex.handle_flow_step(
                        state_manager,
                        flow_type,
                        current_step,
                        message_text
                    )

            # Not in flow - handle member operations
            if not state_manager.get("authenticated"):
                # Attempt login first
                if message_text.lower() in ["hi", "hello"]:
                    return self.auth.handle_greeting(state_manager)
                # Otherwise start registration
                return self.member.start_registration(state_manager)

            # Handle member operations
            if message_text == "upgrade":
                return self.member.start_upgrade(state_manager)

            # Handle account operations
            if message_text == "ledger":
                return self.account.start_ledger(state_manager)

            # Handle credex operations
            if message_text == "offer":
                return self.credex.start_offer(state_manager)
            elif message_text == "accept":
                return self.credex.start_accept(state_manager)

            # Default response
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="I don't understand that command."
            )

        except Exception as e:
            logger.error("Error handling message", extra={
                "error": str(e),
                "message_type": message_type,
                "message_text": message_text
            })
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="❌ An error occurred. Please try again."
            )
