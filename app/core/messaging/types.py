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
    """Base interface for message content"""
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        raise NotImplementedError


@dataclass
class TextContent:
    """Text message content"""
    body: str
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.TEXT)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "type": self.type.value,
            self.type.value: {"body": self.body}
        }
        if self.preview_url:
            result["preview_url"] = self.preview_url
        return result


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
    header: Optional[str] = None
    footer: Optional[str] = None
    buttons: List[Button] = field(default_factory=list)
    action_items: Dict[str, Any] = field(default_factory=dict)
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.INTERACTIVE)

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
    components: List[Dict[str, Any]] = field(default_factory=list)
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.TEMPLATE)

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
class ImageContent:
    """Image message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.IMAGE)

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
class DocumentContent:
    """Document message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.DOCUMENT)

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
class AudioContent:
    """Audio message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.AUDIO)

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
class VideoContent:
    """Video message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.VIDEO)

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
class LocationContent:
    """Location message content"""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.LOCATION)

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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "recipient": self.recipient.to_dict(),
            **self.content.to_dict()
        }
        if self.metadata:
            result["metadata"] = self.metadata.copy()
        return result

    def __str__(self) -> str:
        """String representation for logging"""
        return str(self.to_dict())
