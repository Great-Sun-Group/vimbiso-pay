from core.utils.utils import wrap_text

from .screens import INVALID_ACTION
from .types import BotServiceInterface, WhatsAppMessage


class BaseActionHandler:
    """Base class for WhatsApp action handlers"""

    def __init__(self, service: BotServiceInterface):
        """Initialize the handler with a BotServiceInterface instance

        Args:
            service: Service instance for handling bot interactions
        """
        self.service = service

    def handle_default_action(self) -> WhatsAppMessage:
        """Handle default or unknown actions

        Returns:
            WhatsAppMessage: Error message for invalid actions
        """
        channel_identifier = self.service.user.state.state.get("channel", {}).get("identifier")
        return wrap_text(INVALID_ACTION, channel_identifier)

    @staticmethod
    def format_synopsis(synopsis: str, style: str = None) -> str:
        """Format text synopsis with line breaks for better readability

        Args:
            synopsis: Text to format
            style: Optional style to apply to each word (e.g. '*' for bold)

        Returns:
            str: Formatted text with appropriate line breaks
        """
        formatted_synopsis = ""
        words = synopsis.split()
        line_length = 0

        for word in words:
            # If adding the word exceeds the line length, start a new line
            if line_length + len(word) + 1 > 35:
                formatted_synopsis += "\n"
                line_length = 0
            if style:
                word = f"{style}{word}{style}"
            formatted_synopsis += word + " "
            line_length += len(word) + 1

        return formatted_synopsis.strip()

    def get_response_template(self, message_text: str) -> WhatsAppMessage:
        """Get a basic WhatsApp message template

        Args:
            message_text: Text content for the message

        Returns:
            WhatsAppMessage: Basic formatted WhatsApp message
        """
        channel_identifier = self.service.user.state.state.get("channel", {}).get("identifier")
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_identifier,
            "type": "text",
            "text": {"body": message_text}
        }

    def _format_error_response(self, error_message: str) -> WhatsAppMessage:
        """Format an error response message

        Args:
            error_message: Error message to format

        Returns:
            WhatsAppMessage: Formatted error message
        """
        channel_identifier = self.service.user.state.state.get("channel", {}).get("identifier")
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_identifier,
            "type": "text",
            "text": {
                "body": f"❌ {error_message}"
            }
        }
