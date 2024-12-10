"""WhatsApp service types and interfaces"""
import json
import logging
from typing import Dict, Any
from services.state.service import StateService, StateStage

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
        self.current_state = {}

        # Initialize state service
        from django.core.cache import cache
        self.state = StateService(redis_client=cache)

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
                        self.message_type = "nfm_reply"
                        try:
                            response_json = interactive["nfm_reply"].get("response_json", "{}")
                            self.body = json.loads(response_json)
                        except json.JSONDecodeError:
                            logger.error("Failed to parse nfm_reply response_json")
                            self.body = {}
                else:
                    self.body = ""

            # Get current state using mobile number as user ID
            try:
                self.current_state = self.state.get_state(self.user.mobile_number)
            except Exception as e:
                logger.info(f"No existing state found: {str(e)}")
                # Initialize with empty state but include required fields
                initial_state = {
                    "stage": StateStage.INIT.value,
                    "option": "handle_action_menu",
                    "last_updated": None,
                    "profile": None,
                    "current_account": None
                }
                self.state.update_state(
                    user_id=self.user.mobile_number,
                    new_state=initial_state,
                    stage=StateStage.INIT.value,
                    update_from="init",
                    option="handle_action_menu"
                )
                self.current_state = self.state.get_state(self.user.mobile_number)

            # Update state if body is an action command
            if isinstance(self.body, str) and self.body.startswith("handle_action_"):
                new_state = self.current_state.copy()
                new_state.update({
                    "stage": self.body,
                    "option": self.body,
                    "last_updated": None
                })
                self.state.update_state(
                    user_id=self.user.mobile_number,
                    new_state=new_state,
                    stage=self.body,
                    update_from=self.body,
                    option=self.body
                )
                self.current_state = self.state.get_state(self.user.mobile_number)

        except Exception as e:
            logger.error(f"Error processing message payload: {str(e)}")
            self.message_type = "text"
            self.body = ""

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
            "to": self.user.mobile_number,
            "type": "text",
            "text": {"body": message_text}
        }

    def handle(self) -> Dict[str, Any]:
        """Process the incoming message and generate response"""
        raise NotImplementedError
