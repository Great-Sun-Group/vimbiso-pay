"""Channel-agnostic messaging service"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.messaging.exceptions import (MessageDeliveryError,
                                       MessageTemplateError,
                                       MessageValidationError)
from core.messaging.flow import initialize_flow
from core.messaging.interface import MessagingServiceInterface
from core.messaging.registry import FlowRegistry
from core.messaging.types import (Button, ChannelIdentifier, ChannelType,
                                  Message, MessageRecipient)
from core.utils.error_handler import ErrorHandler
from core.utils.exceptions import (ComponentException, FlowException,
                                   SystemException)

from .account.handlers import AccountHandler
from .credex.handlers import CredexHandler
from .member.handlers import MemberHandler

logger = logging.getLogger(__name__)


class MessagingService(MessagingServiceInterface):
    """Coordinates messaging operations across channels"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        """Initialize with channel-specific messaging service"""
        self.messaging = messaging_service

    def send_message(self, message: Message) -> Message:
        """Send a message to a recipient"""
        return self.messaging.send_message(message)

    def send_text(
        self,
        recipient: MessageRecipient,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send a text message"""
        return self.messaging.send_text(recipient, text, preview_url)

    def send_interactive(
        self,
        recipient: MessageRecipient,
        body: str,
        buttons: List[Button],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Message:
        """Send an interactive message"""
        return self.messaging.send_interactive(
            recipient=recipient,
            body=body,
            buttons=buttons,
            header=header,
            footer=footer
        )

    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Send a template message"""
        return self.messaging.send_template(
            recipient=recipient,
            template_name=template_name,
            language=language,
            components=components
        )

    def validate_message(self, message: Message) -> bool:
        """Validate a message before sending"""
        return self.messaging.validate_message(message)

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
            # Parse command if present
            if "_" in message_text:
                handler_type, command = message_text.split("_", 1)

                # Ensure token still valid before handling command
                if not state_manager.is_authenticated():
                    member_handler = self._get_handler("member")
                    initialize_flow(
                        state_manager=state_manager,
                        flow_type="member_auth",
                        initial_data={
                            "started_at": datetime.utcnow().isoformat()
                        }
                    )
                    return member_handler.handle_flow_step(
                        state_manager=state_manager,
                        flow_type="member_auth",
                        step="greeting",
                        input_value=message_text
                    )

                # Clear flow state before starting new flow
                state_manager.clear_flow_state()

                # Get appropriate handler
                handler = self._get_handler(handler_type)

                # Let handler process command
                try:
                    return handler.handle_command(state_manager, command)
                except FlowException:
                    return self.messaging.send_text(
                        recipient=self._get_recipient(state_manager),
                        text="I don't understand that command."
                    )

            # Check if in active flow
            flow_state = state_manager.get_flow_state()
            if flow_state:
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

            # No active flow - check if greeting
            greetings = [
                # English greetings
                "hi", "hello", "hey", "hie", "menu", "dashboard",
                # Spanish greetings
                "hola", "menu", "tablero",
                # French greetings
                "bonjour", "salut", "menu", "tableau",
                # Shona greetings
                "mhoro", "makadii", "maswera sei", "ndeipi", "zvirisei", "wakadini", "manheru", "masikati",
                # Ndebele greetings
                "sabona", "salibonani", "sawubona", "unjani",
                # Swahili greetings
                "jambo", "habari", "menu", "karibu", "mambo",
                # Common variations
                "start", "begin", "help", "get started", "howzit", "yo", "sup"
            ]
            if message_text.lower() in greetings:
                # Initialize auth flow starting with greeting step
                initialize_flow(
                    state_manager=state_manager,
                    flow_type="member_auth",
                    initial_data={
                        "started_at": datetime.utcnow().isoformat()
                    }
                )

                # Get member handler
                handler = self._get_handler("member")

                # Start with greeting step
                return handler.handle_flow_step(
                    state_manager=state_manager,
                    flow_type="member_auth",
                    step="greeting",
                    input_value=message_text
                )

            # Default response for unhandled messages
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text="👋 Hello and welcome to VimbisoPay. Send me 'hi/ndeipi/sabona' or another greeting to get started!"
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

        except MessageValidationError as e:
            # Handle message validation errors
            error_response = ErrorHandler.handle_system_error(
                code=e.details["code"],
                service=e.details["service"],
                action=e.details["action"],
                message=str(e),
                error=e
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except MessageDeliveryError as e:
            # Handle message delivery errors
            error_response = ErrorHandler.handle_system_error(
                code=e.details["code"],
                service=e.details["service"],
                action=e.details["action"],
                message=str(e),
                error=e
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except MessageTemplateError as e:
            # Handle template errors
            error_response = ErrorHandler.handle_system_error(
                code=e.details["code"],
                service=e.details["service"],
                action=e.details["action"],
                message=str(e),
                error=e
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except (Exception, SystemException) as e:
            # Handle unexpected errors
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
