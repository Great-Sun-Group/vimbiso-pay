from .screens import REGISTER
from .types import WhatsAppMessage


def registration_form(mobile_number: str, message: str = "") -> WhatsAppMessage:
    """Create a WhatsApp registration form message

    Args:
        mobile_number: The recipient's mobile number
        message: Custom message to include in the form (optional)

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
            "body": {"text": REGISTER},  # Using REGISTER directly since it's now a complete message
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
            "body": {
                "text": """
*🔄 New Secured Credex*

Enter amount in USD (default) or specify another denomination:
USD: United States Dollar (e.g. "100")
ZWG: Gold (Zimbabwe Gold) (e.g. "ZWG 100")
XAU: Gold (Troy Ounce) (e.g. "XAU 1")
CAD: Canadian Dollar (e.g. "CAD 100")

"""
            },
            "action": {
                "name": "credex_offer_form",
                "parameters": {
                    "fields": [
                        {
                            "type": "text",
                            "name": "amount",
                            "label": "Amount (with optional denomination)",
                            "required": True
                        },
                        {
                            "type": "text",
                            "name": "recipientAccountHandle",
                            "label": "Recipient Account Handle",
                            "required": True
                        }
                    ]
                }
            }
        }
    }
