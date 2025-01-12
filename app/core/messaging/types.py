"""Message and component types for messaging system"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from core.error.exceptions import ComponentException
from core.messaging.exceptions import MessageValidationError


@dataclass
class MessageRecipient:
    """Message recipient info passed from state to channel services

    Simple wrapper around channel info from state for use in send_* methods.
    The actual channel info lives in state as the single source of truth.
    """
    type: str         # Channel type (e.g. "whatsapp", "sms")
    identifier: str   # Channel ID (e.g. phone number)


@dataclass
class ValidationResult:
    """Result from component validation."""
    valid: bool
    value: Optional[Union[Dict[str, Any], Any]] = None
    metadata: Optional[Dict[str, Any]] = None


# Type for component results that can be ValidationResult, dict, or exception
ComponentResult = Union[ValidationResult, Dict[str, Any], ComponentException]


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
class MessageContent:
    """Base interface for message content"""
    type: MessageType = field(init=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        raise NotImplementedError


@dataclass
class TextContent(MessageContent):
    """Text message content"""
    body: str
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.TEXT)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

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
class Section:
    """Interactive message section"""
    title: str
    rows: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "title": self.title,
            "rows": self.rows
        }


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
class InteractiveContent(MessageContent):
    """Interactive message content"""
    interactive_type: InteractiveType
    body: str
    header: Optional[str] = None
    footer: Optional[str] = None
    buttons: List[Button] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    button_text: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.INTERACTIVE)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

        # Basic structure validation
        if not self.body:
            raise MessageValidationError(
                message="Message body is required",
                service="messaging",
                action="create_message",
                validation_details={
                    "error": "missing_required_field",
                    "field": "body"
                }
            )

        # Validate sections have required fields
        for section in self.sections:
            if not section.title:
                raise MessageValidationError(
                    message="Section title is required",
                    service="messaging",
                    action="create_message",
                    validation_details={
                        "error": "missing_required_field",
                        "field": "section_title"
                    }
                )

            for row in section.rows:
                if "id" not in row or "title" not in row:
                    raise MessageValidationError(
                        message="Row missing required fields (id and title)",
                        service="messaging",
                        action="create_message",
                        validation_details={
                            "error": "missing_required_fields",
                            "section": section.title,
                            "row": row
                        }
                    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "type": self.type.value,
            "interactive": {
                "type": self.interactive_type.value,
                "body": {"text": self.body}
            }
        }

        interactive = result["interactive"]

        # Add header if present
        if self.header:
            interactive["header"] = {
                "type": "text",
                "text": self.header
            }

        # Add footer if present
        if self.footer:
            interactive["footer"] = {
                "text": self.footer
            }

        # Add action based on interactive type
        if self.interactive_type == InteractiveType.BUTTON:
            interactive["action"] = {
                "buttons": [button.to_dict() for button in self.buttons]
            }
        elif self.interactive_type == InteractiveType.LIST:
            interactive["action"] = {
                "button": self.button_text or "Select",
                "sections": [section.to_dict() for section in self.sections]
            }

        return result


@dataclass
class TemplateContent(MessageContent):
    """Template message content"""
    name: str
    language: Dict[str, str]
    components: List[Dict[str, Any]] = field(default_factory=list)
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.TEMPLATE)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

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
class ImageContent(MessageContent):
    """Image message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.IMAGE)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

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
class DocumentContent(MessageContent):
    """Document message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.DOCUMENT)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

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
class AudioContent(MessageContent):
    """Audio message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.AUDIO)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

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
class VideoContent(MessageContent):
    """Video message content"""
    url: str
    caption: Optional[str] = None
    filename: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.VIDEO)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

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
class LocationContent(MessageContent):
    """Location message content"""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None
    preview_url: bool = False
    type: MessageType = field(init=False, default=MessageType.LOCATION)

    def __post_init__(self):
        """Initialize after dataclass creation"""
        super().__init__()

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
    """Message content with optional recipient"""
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
    recipient: Optional[MessageRecipient] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            **self.content.to_dict()
        }
        if self.metadata:
            result["metadata"] = self.metadata.copy()
        return result

    def __str__(self) -> str:
        """String representation for logging"""
        return str(self.to_dict())
