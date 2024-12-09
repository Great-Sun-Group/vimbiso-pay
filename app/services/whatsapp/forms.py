from .screens import REGISTER, OFFER_CREDEX
from .types import WhatsAppMessage


def registration_form(mobile_number: str, message: str) -> WhatsAppMessage:
    """Create a WhatsApp registration form message

    Args:
        mobile_number: The recipient's mobile number
        message: Custom message to include in the form

    Returns:
        WhatsAppMessage: Formatted WhatsApp message with registration form
    """
    return {
        "messaging_product": "whatsapp",
        "to": mobile_number,
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "nfm",
            "body": {"text": REGISTER.format(message=message)},
            "action": {
                "name": "registration_form",
                "parameters": {
                    "fields": [
                        {
                            "type": "text",
                            "name": "firstName",
                            "label": "First Name",
                            "required": True
                        },
                        {
                            "type": "text",
                            "name": "lastName",
                            "label": "Last Name",
                            "required": True
                        }
                    ]
                }
            }
        }
    }


def offer_credex(mobile_number: str, message: str) -> WhatsAppMessage:
    """Create a WhatsApp credex offer form message

    Args:
        mobile_number: The recipient's mobile number
        message: Custom message to include in the form

    Returns:
        WhatsAppMessage: Formatted WhatsApp message with credex offer form
    """
    return {
        "messaging_product": "whatsapp",
        "to": mobile_number,
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "nfm",
            "body": {"text": OFFER_CREDEX.format(message=message)},
            "action": {
                "name": "credex_offer_form",
                "parameters": {
                    "fields": [
                        {
                            "type": "number",
                            "name": "amount",
                            "label": "Amount",
                            "required": True
                        },
                        {
                            "type": "text",
                            "name": "currency",
                            "label": "Currency (e.g. USD)",
                            "required": True
                        },
                        {
                            "type": "text",
                            "name": "handle",
                            "label": "Recipient Handle",
                            "required": True
                        }
                    ]
                }
            }
        }
    }
