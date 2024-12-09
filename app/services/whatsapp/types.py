"""WhatsApp service types and interfaces"""
from typing import Dict, Any


class WhatsAppMessage(Dict[str, Any]):
    """Type for WhatsApp messages"""
    pass


class BotServiceInterface:
    """Interface for bot services"""
    def __init__(self, payload: Dict[str, Any], user: Any) -> None:
        """Initialize the bot service.

        Args:
            payload: Message payload from WhatsApp
            user: CachedUser instance
        """
        self.message = payload
        self.user = user

        # Extract message details from payload
        message_data = (
            payload.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
        )
        messages = message_data.get("messages", [{}])[0]

        # Set message type and body
        self.message_type = messages.get("type", "")
        if self.message_type == "text":
            self.body = messages.get("text", {}).get("body", "")
        elif self.message_type == "button":
            self.body = messages.get("button", {}).get("payload", "")
        elif self.message_type == "interactive":
            self.body = messages.get("interactive", {}).get("button_reply", {}).get("id", "")
        else:
            self.body = ""

        # Initialize state
        self.state = self.user.state
        self.current_state = self.state.get_state(self.user)

    def handle(self) -> Dict[str, Any]:
        """Process the incoming message and generate response"""
        raise NotImplementedError
