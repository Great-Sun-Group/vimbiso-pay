"""Channel-agnostic messaging service"""
import logging
from typing import Any
from datetime import datetime

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.messaging.registry import FlowRegistry
from core.utils.exceptions import ComponentException, FlowException

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

    def _get_handler(self, handler_type: str) -> Any:
        """Get appropriate handler instance"""
        handlers = {
            "member": lambda: MemberHandler(self.messaging),
            "auth": lambda: AuthHandler(self.messaging),
            "account": lambda: AccountHandler(self.messaging),
            "credex": lambda: CredexHandler(self.messaging)
        }
        if handler_type not in handlers:
            raise FlowException(
                message=f"Invalid handler type: {handler_type}",
                step="init",
                action="get_handler",
                data={"handler_type": handler_type}
            )
        return handlers[handler_type]()

    def _get_recipient(self, state_manager: Any) -> MessageRecipient:
        """Get message recipient from state with validation"""
        try:
            return MessageRecipient(
                channel_id=state_manager.get_channel_id(),
                member_id=state_manager.get_member_id()
            )
        except ComponentException:
            # If member_id fails, still return with channel_id
            return MessageRecipient(
                channel_id=state_manager.get_channel_id(),
                member_id=None
            )

    def handle_message(self, state_manager: Any, message_type: str, message_text: str) -> Message:
        """Handle incoming message using appropriate handler"""
        try:
            # Get current flow state for validation tracking
            flow_state = state_manager.get_flow_state()
            if flow_state:
                current_validation = flow_state.get("validation", {})
                current_step_index = flow_state.get("step_index", 0)
                total_steps = flow_state.get("total_steps", 1)

                # Create standardized validation state
                validation_state = {
                    "in_progress": True,
                    "attempts": current_validation.get("attempts", 0) + 1,
                    "last_attempt": {
                        "message": message_text,
                        "type": message_type,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "operation": "handle_message",
                    "component": "message_handler",
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Update state with standardized validation tracking
                state_manager.update_state({
                    "flow_data": {
                        "active_component": {
                            "type": "message_handler",
                            "validation": validation_state
                        },
                        "step_index": current_step_index,
                        "total_steps": total_steps
                    }
                })

                flow_type = state_manager.get_flow_type()
                current_step = state_manager.get_current_step()

                # Get flow config through registry
                config = FlowRegistry.get_flow_config(flow_type)
                handler_type = config.get("handler_type", "member")

                # Get handler instance
                handler = self._get_handler(handler_type)

                # Route to handler
                return handler.handle_flow_step(
                    state_manager,
                    flow_type,
                    current_step,
                    message_text
                )

            # Not in flow - validate auth state with tracking
            flow_data = state_manager.get_flow_data()
            if not flow_data.get("auth", {}).get("authenticated"):
                current_validation = flow_data.get("validation", {})

                # Create standardized validation state
                validation_state = {
                    "in_progress": True,
                    "attempts": current_validation.get("attempts", 0) + 1,
                    "last_attempt": {
                        "message": message_text,
                        "type": message_type,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "operation": "auth_validation",
                    "component": "auth_handler",
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Update state with standardized validation tracking
                state_manager.update_state({
                    "flow_data": {
                        "active_component": {
                            "type": "auth_handler",
                            "validation": validation_state
                        }
                    }
                })

                # Get auth handler
                auth_handler = self._get_handler("auth")
                member_handler = self._get_handler("member")

                # Handle initial greeting
                if message_text.lower() in ["hi", "hello"]:
                    return auth_handler.handle_greeting(state_manager)

                # Start registration
                return member_handler.start_registration(state_manager)

            # Create standardized command validation state
            validation_state = {
                "in_progress": True,
                "attempts": flow_data.get("command_attempts", 0) + 1,
                "last_attempt": {
                    "message": message_text,
                    "type": message_type,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "operation": "handle_command",
                "component": "command_handler",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Update state with standardized command tracking
            state_manager.update_state({
                "flow_data": {
                    "active_component": {
                        "type": "command_handler",
                        "validation": validation_state
                    },
                    "command": {
                        "text": message_text,
                        "type": "user_command",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            })

            # Get appropriate handlers
            member_handler = self._get_handler("member")
            account_handler = self._get_handler("account")
            credex_handler = self._get_handler("credex")

            # Route command through appropriate handler
            if message_text == "upgrade":
                return member_handler.start_upgrade(state_manager)
            elif message_text == "ledger":
                return account_handler.start_ledger(state_manager)
            elif message_text == "offer":
                return credex_handler.start_offer(state_manager)
            elif message_text == "accept":
                return credex_handler.start_accept(state_manager)

            # Update validation state for unknown command
            validation_state.update({
                "in_progress": False,
                "error": {
                    "message": "Unknown command",
                    "details": {
                        "command": message_text,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            })

            # Update state with standardized error tracking
            state_manager.update_state({
                "flow_data": {
                    "active_component": {
                        "type": "command_handler",
                        "validation": validation_state
                    }
                }
            })

            # Send error response
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="I don't understand that command."
            )

        except Exception as e:
            # Create standardized error validation state
            validation_state = {
                "in_progress": False,
                "error": {
                    "message": str(e),
                    "details": {
                        "message_type": message_type,
                        "message_text": message_text,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                "attempts": flow_data.get("error_attempts", 0) + 1,
                "last_attempt": {
                    "message": message_text,
                    "type": message_type,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "operation": "handle_error",
                "component": "error_handler",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Update state with standardized error tracking
            state_manager.update_state({
                "flow_data": {
                    "active_component": {
                        "type": "error_handler",
                        "validation": validation_state
                    }
                }
            })

            logger.error("Error handling message", extra={
                "error": str(e),
                "message_type": message_type,
                "message_text": message_text
            })

            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="❌ An error occurred. Please try again."
            )
