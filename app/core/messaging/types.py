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


@dataclass
class MessageRecipient:
    """Message recipient information"""
    phone_number: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageContent:
    """Base class for message content"""
    type: MessageType
    body: Optional[str] = None
    preview_url: bool = False


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
    action_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TemplateContent:
    """Template message content"""
    name: str
    language: Dict[str, str]
    type: MessageType = field(default=MessageType.TEMPLATE)
    preview_url: bool = False
    components: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MediaContent:
    """Base class for media message content"""
    url: str
    type: MessageType
    preview_url: bool = False
    caption: Optional[str] = None
    filename: Optional[str] = None


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
