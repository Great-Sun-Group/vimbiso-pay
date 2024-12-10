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
                self.current_state = self.state.get_state(self.user.mobile_number)
                logger.debug(f"Current state: {json.dumps(self.current_state, indent=2)}")
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
                logger.debug("Initialized new state")

            # Update state if body is an action command
            if isinstance(self.body, str) and self.body.startswith("handle_action_"):
                logger.debug(f"Updating state for action command: {self.body}")
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
