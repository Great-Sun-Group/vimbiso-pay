from decouple import config
from datetime import datetime, timedelta
from ..config.constants import REGISTER
from .screens import OFFER_CREDEX


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


def offer_credex(mobile_number, message):
    return {
        "messaging_product": "whatsapp",
        "to": mobile_number,
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "body": {
                "text": OFFER_CREDEX.format(message=message)
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_action": "navigate",
                    "flow_token": "not-used",
                    "flow_id": "3435593326740751",
                    "flow_cta": " Offer Secured Credex",
                    "flow_action_payload": {
                        "screen": "MAKE_SECURE_OFFER",
                        "data": {
                            "min_date": str((datetime.now() + timedelta(days=1)).timestamp() * 1000),
                            "max_date": str((datetime.now() + timedelta(weeks=5)).timestamp() * 1000)

                        }
                    }
                }
            }
        }

    }
