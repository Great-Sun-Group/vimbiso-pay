"""Core Messaging Package

This package provides a comprehensive messaging interface with implementations
for different messaging providers. It handles message formatting, validation,
and delivery through various channels.
"""

from typing import Dict, Optional, Type, TypeVar

from .base import BaseMessagingService
from .exceptions import (
    InvalidMessageTypeError,
    InvalidRecipientError,
    MessageDeliveryError,
    MessageFormatError,
    MessageHandlerError,
    MessageRateLimitError,
    MessageTemplateError,
    MessageValidationError,
    TemplateNotFoundError,
    TemplateValidationError,
)
from .interface import MessagingServiceInterface
from .types import (
    AudioContent,
    Button,
    DocumentContent,
    ImageContent,
    InteractiveContent,
    InteractiveType,
    LocationContent,
    Message,
    MessageRecipient,
    MessageType,
    TemplateContent,
    TextContent,
    VideoContent,
)
from .whatsapp import WhatsAppMessagingService

# Type variable for service factory
T = TypeVar('T', bound=BaseMessagingService)


def create_service(
    service_class: Type[T],
    config: Optional[Dict] = None
) -> T:
    """Create a new instance of a messaging service

    Args:
        service_class: The service class to instantiate
        config: Optional configuration dictionary

    Returns:
        An instance of the requested service
    """
    service = service_class()
    if config:
        for key, value in config.items():
            setattr(service, key, value)
    return service


__all__ = [
    # Main interfaces
    'MessagingServiceInterface',
    'BaseMessagingService',

    # Service implementations
    'WhatsAppMessagingService',

    # Message types
    'Message',
    'MessageType',
    'MessageRecipient',
    'TextContent',
    'InteractiveContent',
    'InteractiveType',
    'TemplateContent',
    'AudioContent',
    'VideoContent',
    'ImageContent',
    'DocumentContent',
    'LocationContent',
    'Button',

    # Exceptions
    'MessageHandlerError',
    'MessageValidationError',
    'MessageDeliveryError',
    'MessageTemplateError',
    'MessageFormatError',
    'MessageRateLimitError',
    'InvalidMessageTypeError',
    'InvalidRecipientError',
    'TemplateNotFoundError',
    'TemplateValidationError',

    # Factory function
    'create_service',
]
