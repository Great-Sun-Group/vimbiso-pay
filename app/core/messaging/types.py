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


# WhatsApp Cloud API limits
WHATSAPP_LIMITS = {
    "text_body": 4096,      # Maximum text message length
    "header": 60,           # Maximum header text length
    "footer": 60,           # Maximum footer text length
    "button_text": 20,      # Maximum button text length
    "list_title": 24,       # Maximum list item title length
    "list_description": 72,  # Maximum list item description length
    "buttons_count": 3,     # Maximum number of buttons
    "sections_count": 10,   # Maximum number of sections
    "rows_per_section": 10  # Maximum rows per section
}


@dataclass
class InteractiveContent(MessageContent):
    """Interactive message content following WhatsApp Cloud API format"""
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
        """Initialize after dataclass creation and validate WhatsApp limits"""
        super().__init__()

        # Validate body text
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
        if len(self.body) > WHATSAPP_LIMITS["text_body"]:
            raise MessageValidationError(
                message=f"Body text exceeds {WHATSAPP_LIMITS['text_body']} characters",
                service="messaging",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "body",
                    "length": len(self.body),
                    "max_length": WHATSAPP_LIMITS["text_body"]
                }
            )

        # Validate header/footer length
        if self.header and len(self.header) > WHATSAPP_LIMITS["header"]:
            raise MessageValidationError(
                message=f"Header text exceeds {WHATSAPP_LIMITS['header']} characters",
                service="messaging",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "header",
                    "length": len(self.header),
                    "max_length": WHATSAPP_LIMITS["header"]
                }
            )

        if self.footer and len(self.footer) > WHATSAPP_LIMITS["footer"]:
            raise MessageValidationError(
                message=f"Footer text exceeds {WHATSAPP_LIMITS['footer']} characters",
                service="messaging",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "footer",
                    "length": len(self.footer),
                    "max_length": WHATSAPP_LIMITS["footer"]
                }
            )

        # Validate button text for list messages
        if self.button_text and len(self.button_text) > WHATSAPP_LIMITS["button_text"]:
            raise MessageValidationError(
                message=f"Button text exceeds {WHATSAPP_LIMITS['button_text']} characters",
                service="messaging",
                action="create_message",
                validation_details={
                    "error": "text_too_long",
                    "field": "button_text",
                    "length": len(self.button_text),
                    "max_length": WHATSAPP_LIMITS["button_text"]
                }
            )

        # Validate buttons
        if len(self.buttons) > WHATSAPP_LIMITS["buttons_count"]:
            raise MessageValidationError(
                message=f"Too many buttons (max {WHATSAPP_LIMITS['buttons_count']})",
                service="messaging",
                action="create_message",
                validation_details={
                    "error": "too_many_buttons",
                    "count": len(self.buttons),
                    "max_count": WHATSAPP_LIMITS["buttons_count"]
                }
            )

        # Validate sections
        if len(self.sections) > WHATSAPP_LIMITS["sections_count"]:
            raise MessageValidationError(
                message=f"Too many sections (max {WHATSAPP_LIMITS['sections_count']})",
                service="messaging",
                action="create_message",
                validation_details={
                    "error": "too_many_sections",
                    "count": len(self.sections),
                    "max_count": WHATSAPP_LIMITS["sections_count"]
                }
            )

        # Validate each section
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

            if len(section.title) > WHATSAPP_LIMITS["list_title"]:
                raise MessageValidationError(
                    message=f"Section title exceeds {WHATSAPP_LIMITS['list_title']} characters",
                    service="messaging",
                    action="create_message",
                    validation_details={
                        "error": "text_too_long",
                        "field": "section_title",
                        "section": section.title,
                        "length": len(section.title),
                        "max_length": WHATSAPP_LIMITS["list_title"]
                    }
                )

            if len(section.rows) > WHATSAPP_LIMITS["rows_per_section"]:
                raise MessageValidationError(
                    message=f"Too many rows in section (max {WHATSAPP_LIMITS['rows_per_section']})",
                    service="messaging",
                    action="create_message",
                    validation_details={
                        "error": "too_many_rows",
                        "section": section.title,
                        "count": len(section.rows),
                        "max_count": WHATSAPP_LIMITS["rows_per_section"]
                    }
                )

            # Validate each row
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

                if len(row["title"]) > WHATSAPP_LIMITS["list_title"]:
                    raise MessageValidationError(
                        message=f"Row title exceeds {WHATSAPP_LIMITS['list_title']} characters",
                        service="messaging",
                        action="create_message",
                        validation_details={
                            "error": "text_too_long",
                            "field": "row_title",
                            "section": section.title,
                            "row_title": row["title"],
                            "length": len(row["title"]),
                            "max_length": WHATSAPP_LIMITS["list_title"]
                        }
                    )

                if "description" in row and len(row["description"]) > WHATSAPP_LIMITS["list_description"]:
                    raise MessageValidationError(
                        message=f"Row description exceeds {WHATSAPP_LIMITS['list_description']} characters",
                        service="messaging",
                        action="create_message",
                        validation_details={
                            "error": "text_too_long",
                            "field": "row_description",
                            "section": section.title,
                            "row_title": row["title"],
                            "length": len(row["description"]),
                            "max_length": WHATSAPP_LIMITS["list_description"]
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
