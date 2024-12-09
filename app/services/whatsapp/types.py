from typing import TypedDict, Dict, Any


class WhatsAppMessage(TypedDict):
    """Type definition for WhatsApp message structure"""
    messaging_product: str
    to: str
    recipient_type: str
    type: str
    interactive: Dict[str, Any]


class CredexBotService:
    """Type stub for CredexBotService"""
    user: Any
    message: Dict[str, Any]
    body: Any
    current_state: Dict[str, Any]
    state_manager: Any
    api_interactions: Any
