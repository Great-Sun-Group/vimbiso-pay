"""Core messaging service package

This package provides the messaging service orchestration layer that:
1. Implements the core messaging interfaces
2. Manages channel-specific implementations
3. Maintains consistent interface across channels
"""
from .service import MessagingService

__all__ = ['MessagingService']
