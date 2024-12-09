from core.utils.utils import wrap_text
from .screens import INVALID_ACTION
from .types import CredexBotService, WhatsAppMessage


class BaseActionHandler:
    """Base class for WhatsApp action handlers"""

    def __init__(self, service: "CredexBotService"):
        """Initialize the handler with a CredexBotService instance

        Args:
            service: Service instance for handling bot interactions
        """
        self.service = service

    def handle_default_action(self) -> WhatsAppMessage:
        """Handle default or unknown actions

        Returns:
            WhatsAppMessage: Error message for invalid actions
        """
        return wrap_text(INVALID_ACTION, self.service.user.mobile_number)

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
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.service.user.mobile_number,
            "type": "text",
            "text": {"body": message_text}
        }
