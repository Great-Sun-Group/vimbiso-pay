from decouple import config
from ..config.constants import REGISTER


def registration_form(mobile_number, message):
    return {
        "messaging_product": "whatsapp",
        "to": mobile_number,
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "body": {
                "text": REGISTER.format(message=message)
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_action": "navigate",
                    "flow_token": "not-used",
                    "flow_id": "3686836301579704",
                    "flow_cta": "Create Account",
                    "flow_action_payload": {
                        "screen": "MEMBER_SIGNUP"
                    }
                }
            }
        }
        
        }