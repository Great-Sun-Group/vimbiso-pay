"""Core Messaging System

This package provides a channel-agnostic messaging system for handling all user
communication through a layered architecture. It includes message formatting,
template management, and interactive elements.

For specific messaging implementations, see services/messaging/
"""

from .service import MessagingService
from .types import Message, TextContent
from .utils import get_recipient

__all__ = [
    'MessagingService',
    'Message',
    'TextContent',
    'get_recipient'
]
