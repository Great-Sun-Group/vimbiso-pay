"""Messaging service implementation

This service handles message processing and responses.
Flow routing is handled by core/messaging/flow.py.
Component processing is handled by the components themselves.
Message formatting is handled by formatters.py.
"""

import logging
from typing import Any, Dict, Optional

from core.messaging.flow import process_component
from core.messaging.base import BaseMessagingService
from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, TextContent
from core.utils.exceptions import SystemException
from core.messaging.formatters.formatters import AccountFormatters
from core.messaging.utils import get_recipient

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

            # Get recipient for message
            recipient = get_recipient(self.state_manager)

            # Format appropriate message based on context/component
            match (next_context, next_component):
                case ("account", "AccountDashboard"):
                    # Format dashboard using account data
                    active_account = result["active_account"]
                    balance_data = active_account.get("balanceData", {})

                    # Get member tier from dashboard data
                    member_data = result["dashboard"].get("member", {})
                    member_tier = member_data.get("memberTier")
                    account_data = {
                        "accountName": active_account.get("accountName"),
                        "accountHandle": active_account.get("accountHandle"),
                        "netCredexAssetsInDefaultDenom": balance_data.get('netCredexAssetsInDefaultDenom', '0.00'),
                        "defaultDenom": member_data.get('defaultDenom', 'USD'),
                        **balance_data
                    }

                    # Only include tier limit for tier < 2
                    if member_tier < 2:
                        account_data["tier_limit_raw"] = member_data.get("remainingAvailableUSD", "0.00")

                    message = AccountFormatters.format_dashboard(account_data)

                    # Check if we should use interactive format
                    if "buttons" in result:
                        # Use button format for simple interactions
                        return self.send_interactive(
                            recipient=recipient,
                            body=message,
                            buttons=result["buttons"][:3]  # Limit to 3 buttons for WhatsApp
                        )
                    elif result.get("use_list"):
                        # Use list format for multiple options
                        return self.send_interactive(
                            recipient=recipient,
                            body=message,
                            sections=result["sections"],
                            button_text=result.get("button_text", "Select Option")
                        )
                    else:
                        # Fallback to simple text message
                        return Message(
                            recipient=recipient,
                            content=TextContent(body=message)
                        )

                case (_, "Greeting"):
                    # Simple text message for greetings
                    return Message(
                        recipient=recipient,
                        content=TextContent(body=result)
                    )

                case _:
                    # For other cases, check result type
                    if isinstance(result, str):
                        return Message(
                            recipient=recipient,
                            content=TextContent(body=result)
                        )
                    elif isinstance(result, dict) and "error" in result:
                        return Message(
                            recipient=recipient,
                            content=TextContent(body=f"⚠️ {result['error']}")
                        )
                    else:
                        logger.info(
                            f"No message handler for {next_context}/{next_component}"
                        )
                        return None

        except SystemException as e:
            if "rate limit" in str(e).lower():
                return Message(
                    recipient=get_recipient(self.state_manager),
                    content=TextContent(
                        body="⚠️ Too many messages sent. Please wait a moment before trying again."
                    )
                )
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
