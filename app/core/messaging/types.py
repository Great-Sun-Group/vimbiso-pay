"""Message types for WhatsApp interactions"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MessageType(Enum):
    """Types of messages that can be sent"""
    TEXT = "text"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"


class InteractiveType(Enum):
    """Types of interactive messages"""
    LIST = "list"
    BUTTON = "button"
    PRODUCT = "product"
    PRODUCT_LIST = "product_list"


class ChannelType(Enum):
    """Supported messaging channels"""
    WHATSAPP = "whatsapp"
    # Future channels can be added here
    # SMS = "sms"
    # TELEGRAM = "telegram"
    # etc.


@dataclass
class ChannelIdentifier:
    """Channel-specific identifier information"""
    channel: ChannelType
    value: str  # The channel-specific ID (phone number for WhatsApp, etc)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "channel": self.channel.value,
            "value": self.value,
            "metadata": self.metadata
        }


@dataclass
class MessageRecipient:
    """Message recipient information"""
    channel_id: ChannelIdentifier  # Channel-specific identifier
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "channel": self.channel_id.to_dict()
        }
        if self.name:
            result["name"] = self.name
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @property
    def channel_value(self) -> str:
        """Get the channel-specific identifier value"""
        return self.channel_id.value


@dataclass
class MessageContent:
    """Base class for message content"""
    type: MessageType
    body: Optional[str] = None
    preview_url: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {"type": self.type.value}
        if self.body:
            result[self.type.value] = {"body": self.body}
        if self.preview_url:
            result["preview_url"] = self.preview_url
        return result


@dataclass
class TextContent(MessageContent):
    """Text message content"""
    def __init__(self, body: str):
        super().__init__(type=MessageType.TEXT)
        self.body = body


@dataclass
class Button:
    """Interactive button"""
    id: str
    title: str
    type: str = "reply"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "type": self.type,
            "reply": {
                "id": self.id,
                "title": self.title
            }
        }


@dataclass
class InteractiveContent:
    """Interactive message content"""
    interactive_type: InteractiveType
    body: str
    type: MessageType = field(default=MessageType.INTERACTIVE)
    preview_url: bool = False
    header: Optional[str] = None
    footer: Optional[str] = None
    buttons: List[Button] = field(default_factory=list)
    action_items: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        interactive = {
            "type": self.interactive_type.value,
            "body": {"text": self.body}
        }

        # Add header if present
        if self.header:
            interactive["header"] = {"type": "text", "text": self.header}

        # Add footer if present
        if self.footer:
            interactive["footer"] = {"text": self.footer}

        # Add action based on interactive type
        if self.interactive_type == InteractiveType.BUTTON:
            interactive["action"] = {
                "buttons": [button.to_dict() for button in self.buttons]
            }
        elif self.interactive_type == InteractiveType.LIST:
            # For list type, action_items should contain button and sections
            if not self.action_items:
                interactive["action"] = {
                    "button": "Select",
                    "sections": []
                }
            else:
                interactive["action"] = self.action_items

        return {
            "type": self.type.value,
            "interactive": interactive
        }


@dataclass
class TemplateContent:
    """Template message content"""
    name: str
    language: Dict[str, str]
    type: MessageType = field(default=MessageType.TEMPLATE)
    preview_url: bool = False
    components: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "type": self.type.value,
            "template": {
                "name": self.name,
                "language": self.language
            }
        }
        if self.components:
            result["template"]["components"] = self.components
        if self.preview_url:
            result["preview_url"] = self.preview_url
        return result


@dataclass
class MediaContent:
    """Base class for media message content"""
    url: str
    type: MessageType
    preview_url: bool = False
    caption: Optional[str] = None
    filename: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "type": self.type.value,
            self.type.value: {"url": self.url}
        }
        if self.caption:
            result[self.type.value]["caption"] = self.caption
        if self.filename:
            result[self.type.value]["filename"] = self.filename
        if self.preview_url:
            result["preview_url"] = self.preview_url
        return result


@dataclass
class ImageContent(MediaContent):
    """Image message content"""
    def __init__(self, url: str, **kwargs):
        super().__init__(url=url, type=MessageType.IMAGE, **kwargs)


@dataclass
class DocumentContent(MediaContent):
    """Document message content"""
    def __init__(self, url: str, **kwargs):
        super().__init__(url=url, type=MessageType.DOCUMENT, **kwargs)


@dataclass
class AudioContent(MediaContent):
    """Audio message content"""
    def __init__(self, url: str, **kwargs):
        super().__init__(url=url, type=MessageType.AUDIO, **kwargs)


@dataclass
class VideoContent(MediaContent):
    """Video message content"""
    def __init__(self, url: str, **kwargs):
        super().__init__(url=url, type=MessageType.VIDEO, **kwargs)


@dataclass
class LocationContent:
    """Location message content"""
    latitude: float
    longitude: float
    type: MessageType = field(default=MessageType.LOCATION)
    preview_url: bool = False
    name: Optional[str] = None
    address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "type": self.type.value,
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude
            }
        }
        if self.name:
            result["location"]["name"] = self.name
        if self.address:
            result["location"]["address"] = self.address
        if self.preview_url:
            result["preview_url"] = self.preview_url
        return result


@dataclass
class Message:
    """Complete message with recipient and content"""
    recipient: MessageRecipient
    content: Union[
        TextContent,
        InteractiveContent,
        TemplateContent,
        ImageContent,
        DocumentContent,
        AudioContent,
        VideoContent,
        LocationContent,
    ]
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "messaging_product": self.messaging_product,
            "recipient_type": self.recipient_type,
            "to": self.recipient.channel_value,  # Use channel-specific identifier
            **self.content.to_dict()
        }
        # Only include non-state metadata if present
        if self.metadata:
            result["metadata"] = self.metadata.copy()  # Create copy to avoid modifying original
        return result

    def __str__(self) -> str:
        """String representation for logging"""
        return str(self.to_dict())
