"""Channel-agnostic messaging service"""
import logging
from datetime import datetime
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.flow import initialize_flow
from core.messaging.registry import FlowRegistry
from core.messaging.types import (
    ChannelIdentifier,
    ChannelType,
    Message,
    MessageRecipient
)
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import ComponentException, FlowException

from .account.handlers import AccountHandler
from .credex.handlers import CredexHandler
from .member.handlers import MemberHandler

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
            # Create proper channel identifier
            channel_id = ChannelIdentifier(
                channel=ChannelType.WHATSAPP,
                value=state_manager.get_channel_id()
            )
            return MessageRecipient(channel_id=channel_id)
        except ComponentException as e:
            logger.error(f"Error creating recipient: {str(e)}")
            raise

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

                # Get member handler for both auth and registration
                member_handler = self._get_handler("member")

                # Initialize auth flow for greeting
                if message_text.lower() in ["hi", "hello"]:
                    initialize_flow(
                        state_manager=state_manager,
                        flow_type="auth",
                        initial_data={
                            "started_at": datetime.utcnow().isoformat()
                        }
                    )
                    return member_handler.handle_flow_step(
                        state_manager=state_manager,
                        flow_type="auth",
                        step="login",
                        input_value=message_text
                    )

                # Start registration for new users
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

        except FlowException as e:
            # Handle flow errors
            error_response = ErrorHandler.handle_flow_error(
                step=e.step,
                action=e.action,
                data=e.data,
                message=str(e),
                flow_state=flow_state if 'flow_state' in locals() else None
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except ComponentException as e:
            # Handle component errors
            error_response = ErrorHandler.handle_component_error(
                component=e.component,
                field=e.field,
                value=e.value,
                message=str(e)
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except Exception as e:
            # Handle system errors
            error_response = ErrorHandler.handle_system_error(
                code="MESSAGE_ERROR",
                service="messaging",
                action="handle_message",
                message=str(e),
                error=e
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )
