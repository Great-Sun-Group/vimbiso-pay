"""Message and component types for messaging system"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from core.error.exceptions import ComponentException
from core.messaging.exceptions import MessageValidationError


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

        # Validate text lengths (WhatsApp limits)
        if len(self.body) > 4096:
            raise MessageValidationError(
                message="Body text exceeds 4096 characters",
                service="whatsapp",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "body",
                    "length": len(self.body),
                    "max_length": 4096
                }
            )

        if self.header and len(self.header) > 60:
            raise MessageValidationError(
                message="Header text exceeds 60 characters",
                service="whatsapp",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "header",
                    "length": len(self.header),
                    "max_length": 60
                }
            )

        if self.footer and len(self.footer) > 60:
            raise MessageValidationError(
                message="Footer text exceeds 60 characters",
                service="whatsapp",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "footer",
                    "length": len(self.footer),
                    "max_length": 60
                }
            )

        if self.button_text and len(self.button_text) > 20:
            raise MessageValidationError(
                message="Button text exceeds 20 characters",
                service="whatsapp",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "button_text",
                    "length": len(self.button_text),
                    "max_length": 20
                }
            )

        # Validate sections (WhatsApp limits)
        if len(self.sections) > 10:
            raise MessageValidationError(
                message="Too many sections (max 10)",
                service="whatsapp",
                action="create_message",
                validation_details={
                    "error": "too_many_sections",
                    "count": len(self.sections),
                    "max_count": 10
                }
            )

        for section in self.sections:
            # Validate section title length
            if len(section.title) > 24:
                raise MessageValidationError(
                    message="Section title exceeds 24 characters",
                    service="whatsapp",
                    action="create_message",
                    validation_details={
                        "error": "text_too_long",
                        "field": "section_title",
                        "section": section.title,
                        "length": len(section.title),
                        "max_length": 24
                    }
                )

            # Validate rows
            if len(section.rows) > 10:
                raise MessageValidationError(
                    message=f"Too many rows in section '{section.title}' (max 10)",
                    service="whatsapp",
                    action="create_message",
                    validation_details={
                        "error": "too_many_rows",
                        "section": section.title,
                        "count": len(section.rows),
                        "max_count": 10
                    }
                )

            for row in section.rows:
                # Validate required fields
                if "id" not in row or "title" not in row:
                    raise MessageValidationError(
                        message="Row missing required fields (id and title)",
                        service="whatsapp",
                        action="create_message",
                        validation_details={
                            "error": "missing_required_fields",
                            "section": section.title,
                            "row": row
                        }
                    )

                # Validate row ID length
                if len(row["id"]) > 200:
                    raise MessageValidationError(
                        message="Row ID exceeds 200 characters",
                        service="whatsapp",
                        action="create_message",
                        validation_details={
                            "error": "text_too_long",
                            "field": "row_id",
                            "section": section.title,
                            "row_id": row["id"],
                            "length": len(row["id"]),
                            "max_length": 200
                        }
                    )

                # Validate row title length
                if len(row["title"]) > 24:
                    raise MessageValidationError(
                        message="Row title exceeds 24 characters",
                        service="whatsapp",
                        action="create_message",
                        validation_details={
                            "error": "text_too_long",
                            "field": "row_title",
                            "section": section.title,
                            "row_title": row["title"],
                            "length": len(row["title"]),
                            "max_length": 24
                        }
                    )

                # Validate row description length if present
                if "description" in row and len(row["description"]) > 72:
                    raise MessageValidationError(
                        message="Row description exceeds 72 characters",
                        service="whatsapp",
                        action="create_message",
                        validation_details={
                            "error": "text_too_long",
                            "field": "row_description",
                            "section": section.title,
                            "row_title": row["title"],
                            "length": len(row["description"]),
                            "max_length": 72
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
            if len(self.buttons) > 3:  # WhatsApp limit
                raise MessageValidationError(
                    message="Too many buttons (max 3)",
                    service="whatsapp",
                    action="create_message",
                    validation_details={
                        "error": "too_many_buttons",
                        "count": len(self.buttons),
                        "max_count": 3
                    }
                )
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
