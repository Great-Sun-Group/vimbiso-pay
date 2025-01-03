"""SMS-specific message types"""
from dataclasses import dataclass
from typing import Dict, Optional

from core.messaging.types import Message


@dataclass
class SMSMessage:
    """SMS message format"""
    to: str
    body: str
    metadata: Optional[Dict] = None

    @classmethod
    def from_core_message(cls, message: Message) -> "SMSMessage":
        """Convert core Message to SMS format"""
        return cls(
            to=message.recipient.channel_id.value,
            body=message.content.body,
            metadata=message.metadata
        )

    @classmethod
    def create_text(cls, recipient: str, text: str) -> "SMSMessage":
        """Create text message"""
        return cls(
            to=recipient,
            body=text
        )
