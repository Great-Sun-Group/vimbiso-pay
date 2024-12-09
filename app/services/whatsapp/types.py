"""WhatsApp service types and interfaces"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

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
        try:
            # Try direct message format first (mock server)
            self.message_type = payload.get("type", "")
            if self.message_type == "text":
                self.body = payload.get("message", "")
            elif self.message_type == "button":
                self.body = payload.get("message", "")
            elif self.message_type == "interactive":
                self.body = payload.get("message", "")
            else:
                self.body = payload.get("message", "")

            # If no message type found, try nested format (WhatsApp API)
            if not self.message_type:
                message_data = (
                    payload.get("entry", [{}])[0]
                    .get("changes", [{}])[0]
                    .get("value", {})
                )
                messages = message_data.get("messages", [{}])[0]
                self.message_type = messages.get("type", "")

                if self.message_type == "text":
                    self.body = messages.get("text", {}).get("body", "")
                elif self.message_type == "button":
                    self.body = messages.get("button", {}).get("payload", "")
                elif self.message_type == "interactive":
                    interactive = messages.get("interactive", {})
                    if "button_reply" in interactive:
                        self.body = interactive["button_reply"].get("id", "")
                    elif "list_reply" in interactive:
                        self.body = interactive["list_reply"].get("id", "")
                    elif "nfm_reply" in interactive:
        if self.body and self.body.startswith("handle_action_"):
            self.state.update_state(
                state=self.current_state,
                stage=self.body,
                update_from=self.body,
                option=self.body
            )
            self.current_state = self.state.get_state(self.user)

    def handle(self) -> Dict[str, Any]:
        """Process the incoming message and generate response"""
        raise NotImplementedError
