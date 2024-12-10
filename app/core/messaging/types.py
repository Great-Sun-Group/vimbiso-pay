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
    preview_url: bool = False


@dataclass
class TextContent(MessageContent):
    """Text message content"""
    body: str

    def __post_init__(self):
        self.type = MessageType.TEXT


@dataclass
class Button:
    """Interactive button"""
    id: str
    title: str
    type: str = "reply"


@dataclass
class InteractiveContent(MessageContent):
    """Interactive message content"""
    type: MessageType = field(default=MessageType.INTERACTIVE)
    interactive_type: InteractiveType = field(default=InteractiveType.BUTTON)
    header: Optional[str] = None
    body: str = ""
    footer: Optional[str] = None
    buttons: List[Button] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TemplateContent(MessageContent):
    """Template message content"""
    name: str
    language: Dict[str, str]
    components: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.type = MessageType.TEMPLATE


@dataclass
class MediaContent(MessageContent):
    """Base class for media message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None


@dataclass
class ImageContent(MediaContent):
    """Image message content"""
    def __post_init__(self):
        self.type = MessageType.IMAGE


@dataclass
class DocumentContent(MediaContent):
    """Document message content"""
    def __post_init__(self):
        self.type = MessageType.DOCUMENT


@dataclass
class AudioContent(MediaContent):
    """Audio message content"""
    def __post_init__(self):
        self.type = MessageType.AUDIO


@dataclass
class VideoContent(MediaContent):
    """Video message content"""
    def __post_init__(self):
        self.type = MessageType.VIDEO


@dataclass
class LocationContent(MessageContent):
    """Location message content"""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None

    def __post_init__(self):
        self.type = MessageType.LOCATION


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
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
