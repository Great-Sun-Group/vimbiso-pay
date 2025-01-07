"""Messaging service implementation

This service handles message processing and responses.
Flow routing is handled by core/messaging/flow.py.
Component processing is handled by the components themselves.
Message formatting is handled by handlers.py.
"""

import logging
from typing import Any, Dict, Optional

from core.messaging.flow import process_component
from core.messaging.base import BaseMessagingService
from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message
from core.utils.exceptions import SystemException

from . import handlers

logger = logging.getLogger(__name__)


class MessagingService(MessagingServiceInterface):
    """Main messaging service"""

    def __init__(self, channel_service: BaseMessagingService, state_manager: Any):
        """Initialize messaging service

        Args:
            channel_service: Channel-specific messaging service (WhatsApp, SMS, etc)
            state_manager: State manager for tracking state
        """
        self.channel_service = channel_service
        self.state_manager = state_manager

        # Set state manager on channel service
        if hasattr(self.channel_service, 'state_manager'):
            self.channel_service.state_manager = state_manager

    def handle_message(self) -> Optional[Message]:
        """Handle incoming message

        The flow is:
        1. Get message data from state
        2. Get current context/component from state
        3. Process component with input
        4. Get next context/component
        5. Format and send appropriate message

        Returns:
            Optional[Message]: Response message if any
        """
        try:
            # Get message data from state
            message_data = self.state_manager.get("message", {})
            if not message_data:
                raise ValueError("No message data in state")

            # Get current context and component
            context = self.state_manager.get_context()
            component = self.state_manager.get_component()

            # Process component using state manager
            result, next_context, next_component = process_component(
                context or "login",  # Default to login context
                component or "Greeting",  # Default to greeting component
                self.state_manager
            )

            # Update state
            self.state_manager.update_flow_state(
                next_context,
                next_component,
                {"result": result}
            )

            # Format appropriate message based on context/component
            match (next_context, next_component):
                case ("account", "AccountDashboard"):
                    return handlers.handle_dashboard_display(
                        messaging_service=self,
                        state_manager=self.state_manager,
                        verified_data=result
                    )

                case (_, "Greeting"):
                    return handlers.handle_greeting(
                        state_manager=self.state_manager,
                        content=result
                    )

                case _:
                    # For other cases, check result type
                    if isinstance(result, str):
                        return handlers.handle_greeting(
                            state_manager=self.state_manager,
                            content=result
                        )
                    elif isinstance(result, dict) and "error" in result:
                        return handlers.handle_error(
                            state_manager=self.state_manager,
                            error=result["error"]
                        )
                    else:
                        logger.info(
                            f"No message handler for {next_context}/{next_component}"
                        )
                        return None

        except SystemException as e:
            if "rate limit" in str(e).lower():
                return handlers.handle_rate_limit_error(self.state_manager)
            raise

    def send_message(self, message: Message) -> Message:
        """Send message through channel service"""
        return self.channel_service.send_message(message)

    def send_text(
        self,
        recipient,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send text message through channel service"""
        return self.channel_service.send_text(recipient, text, preview_url)

    def send_interactive(
        self,
        recipient,
        body: str,
        buttons=None,
        header=None,
        footer=None,
        sections=None,
        button_text=None
    ) -> Message:
        """Send interactive message through channel service"""
        return self.channel_service.send_interactive(
            recipient=recipient,
            body=body,
            buttons=buttons,
            header=header,
            footer=footer,
            sections=sections,
            button_text=button_text
        )

    def send_template(
        self,
        recipient,
        template_name: str,
        language: Dict[str, str],
        components=None
    ) -> Message:
        """Send template message through channel service"""
        return self.channel_service.send_template(
            recipient=recipient,
            template_name=template_name,
            language=language,
            components=components
        )

    def validate_message(self, message: Message) -> bool:
        """Validate message format"""
        # Implementation depends on channel type
        raise NotImplementedError
