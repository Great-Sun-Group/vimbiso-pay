"""WhatsApp service types and interfaces"""
import json
import logging
from typing import Any, Dict, Union

from core.messaging.types import Message as CoreMessage
from services.state.service import StateService, StateStage

logger = logging.getLogger(__name__)


class WhatsAppMessage(Dict[str, Any]):
    """Type for WhatsApp messages"""

    @classmethod
    def from_core_message(cls, message: Union[CoreMessage, Dict[str, Any], 'WhatsAppMessage']) -> Dict[str, Any]:
        """Convert core message to WhatsApp message format"""
        try:
            # If it's already a dict in WhatsApp format, return it
            if isinstance(message, dict):
                if "messaging_product" in message:
                    return message
                # If it's a dict but not in WhatsApp format, wrap it
                if "type" not in message:
                    message["type"] = "text"
                if message["type"] == "text" and "text" not in message:
                    message["text"] = {"body": str(message.get("body", ""))}
                return {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    **message
                }

            # If it's a WhatsAppMessage from core, convert it
            if isinstance(message, CoreMessage):
                content_type = message.content.type.value
                content_dict = {}
                if content_type == "text":
                    content_dict = {"body": message.content.body}
                elif content_type == "interactive":
                    content_dict = message.content.to_dict()
                else:
                    content_dict = message.content.to_dict()

                return {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": message.recipient.phone_number,
                    "type": content_type,
                    content_type: content_dict
                }

            # If it's already a WhatsAppMessage instance, convert to dict
            if isinstance(message, WhatsAppMessage):
                return dict(message)

            raise TypeError(f"Cannot convert {type(message)} to WhatsApp message format")
        except Exception as e:
            logger.error(f"Error converting message: {str(e)}")
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "type": "text",
                "text": {
                    "body": f"Error converting message: {str(e)}"
                }
            }


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
            # Extract message from WhatsApp webhook format
            message_data = (
                payload.get("entry", [{}])[0]
                .get("changes", [{}])[0]
                .get("value", {})
            )
            messages = message_data.get("messages", [{}])
            if not messages:
                logger.error("No messages found in payload")
                raise ValueError("No messages found in payload")

            message = messages[0]
            self.message_type = message.get("type", "")
            logger.debug(f"Message type: {self.message_type}")

            # Extract body based on message type
            if self.message_type == "text":
                self.body = message.get("text", {}).get("body", "")
                logger.debug(f"Text message body: {self.body}")
            elif self.message_type == "button":
                self.body = message.get("button", {}).get("payload", "")
                logger.debug(f"Button payload: {self.body}")
            elif self.message_type == "interactive":
                interactive = message.get("interactive", {})
                logger.debug(f"Interactive message: {json.dumps(interactive, indent=2)}")
                if "button_reply" in interactive:
                    self.body = interactive["button_reply"].get("id", "")
                    logger.debug(f"Button reply ID: {self.body}")
                elif "list_reply" in interactive:
                    self.body = interactive["list_reply"].get("id", "")
                    logger.debug(f"List reply ID: {self.body}")
                elif "nfm_reply" in interactive:
                    self.message_type = "nfm_reply"
                    try:
                        # More lenient form data extraction
                        nfm_reply = interactive["nfm_reply"]
                        form_data = {}

                        # Try different possible locations for form data
                        if "submitted_form_data" in nfm_reply:
                            submitted_form = nfm_reply["submitted_form_data"]
                            # Try form_data.response_fields path
                            if "form_data" in submitted_form:
                                form_data_obj = submitted_form["form_data"]
                                if "response_fields" in form_data_obj:
                                    for field in form_data_obj["response_fields"]:
                                        if "field_id" in field and "value" in field:
                                            form_data[field["field_id"]] = field["value"]
                                # Also try response_payload.response_json path
                                elif "response_payload" in form_data_obj:
                                    try:
                                        response_json = form_data_obj["response_payload"].get("response_json")
                                        if response_json:
                                            json_data = json.loads(response_json)
                                            form_data.update(json_data)
                                    except (json.JSONDecodeError, AttributeError):
                                        pass

                        # Fallback to direct response_json if exists
                        if not form_data and "response_json" in nfm_reply:
                            try:
                                json_data = json.loads(nfm_reply["response_json"])
                                form_data.update(json_data)
                            except (json.JSONDecodeError, AttributeError):
                                pass

                        self.body = form_data
                        logger.debug(f"Extracted form data: {json.dumps(self.body, indent=2)}")
                    except Exception as e:
                        logger.error(f"Error extracting form data: {str(e)}")
                        self.body = {}
            else:
                logger.warning(f"Unsupported message type: {self.message_type}")
                self.body = ""

            # Get current state using mobile number as user ID
            try:
                state_data = self.state.get_state(self.user.mobile_number)
                logger.debug(f"Retrieved state data: {json.dumps(state_data, indent=2)}")

                # Parse state if it's a string and preserve jwt_token
                jwt_token = state_data.get("jwt_token")  # Save JWT token
                if isinstance(state_data.get("state"), str):
                    try:
                        parsed_state = json.loads(state_data["state"])
                        logger.debug(f"Parsed state: {json.dumps(parsed_state, indent=2)}")
                        # Update state with parsed data
                        state_data.update(parsed_state)
                        # Remove the original string state
                        state_data.pop("state", None)
                    except json.JSONDecodeError:
                        logger.error("Failed to parse state JSON")
                        state_data = {}

                # Restore JWT token if it was present
                if jwt_token:
                    state_data["jwt_token"] = jwt_token
                    logger.debug("Restored JWT token after state parsing")

                # Initialize state with proper structure if empty
                if not state_data or not isinstance(state_data, dict):
                    state_data = {
                        "stage": StateStage.INIT.value,
                        "option": "handle_action_menu",
                        "last_updated": None,
                        "profile": {
                            "data": {
                                "action": {"details": {}},
                                "dashboard": {}
                            }
                        },
                        "current_account": None
                    }
                    # Preserve JWT token in new state
                    if jwt_token:
                        state_data["jwt_token"] = jwt_token

                # Ensure profile has proper structure
                if "profile" not in state_data:
                    state_data["profile"] = {
                        "data": {
                            "action": {"details": {}},
                            "dashboard": {}
                        }
                    }
                elif isinstance(state_data["profile"], dict):
                    if "data" not in state_data["profile"]:
                        state_data["profile"] = {"data": state_data["profile"]}
                    if "action" not in state_data["profile"]["data"]:
                        state_data["profile"]["data"]["action"] = {"details": {}}
                    elif "details" not in state_data["profile"]["data"]["action"]:
                        state_data["profile"]["data"]["action"]["details"] = {}

                self.current_state = state_data
                logger.debug(f"Using state: {json.dumps(self.current_state, indent=2)}")

            except Exception as e:
                logger.info(f"No existing state found: {str(e)}")
                # Initialize with empty state but include required fields
                initial_state = {
                    "stage": StateStage.INIT.value,
                    "option": "handle_action_menu",
                    "last_updated": None,
                    "profile": {
                        "data": {
                            "action": {"details": {}},
                            "dashboard": {}
                        }
                    },
                    "current_account": None
                }
                # Preserve JWT token in initial state if it exists
                if jwt_token:
                    initial_state["jwt_token"] = jwt_token

                self.state.update_state(
                    user_id=self.user.mobile_number,
                    new_state=initial_state,
                    stage=StateStage.INIT.value,
                    update_from="init",
                    option="handle_action_menu"
                )
                self.current_state = initial_state
                logger.debug("Initialized new state")

        except Exception as e:
            logger.error(f"Error processing message payload: {str(e)}")
            self.message_type = "text"
            self.body = ""

    def get_response_template(self, message_text: str) -> Dict[str, Any]:
        """Get a basic WhatsApp message template

        Args:
            message_text: Text content for the message

        Returns:
            Dict[str, Any]: Basic formatted WhatsApp message
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
