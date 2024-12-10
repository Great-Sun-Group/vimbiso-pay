"""CredEx Service Package

This package provides a comprehensive interface for interacting with the CredEx API.
It handles authentication, member management, and CredEx offer operations.
"""

from typing import Dict, Optional, Type, TypeVar

from .auth import CredExAuthService
from .base import BaseCredExService
from .config import CredExConfig, CredExEndpoints
from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    CredExServiceError,
    InvalidCredExOfferError,
    InvalidHandleError,
    MemberNotFoundError,
    NetworkError,
    ResourceNotFoundError,
    ValidationError,
)
from .interface import CredExServiceInterface
from .member import CredExMemberService
from .offers import CredExOffersService
from .service import CredExService

# Type variable for service factory
T = TypeVar('T', bound=BaseCredExService)


def create_service(
    service_class: Type[T],
    config: Optional[CredExConfig] = None
) -> T:
    """Create a new instance of a CredEx service

    Args:
        service_class: The service class to instantiate
        config: Optional configuration. If not provided, loads from environment.

    Returns:
        An instance of the requested service
    """
    return service_class(config=config)


def create_from_config(config_dict: Dict) -> CredExService:
    """Create a CredEx service from a configuration dictionary

    Args:
        config_dict: Configuration dictionary

    Returns:
        Configured CredEx service instance
    """
    config = CredExConfig.from_env()
    for key, value in config_dict.items():
        setattr(config, key, value)
    return CredExService(config=config)


__all__ = [
    # Main service
    'CredExService',
    'CredExServiceInterface',

    # Component services
    'CredExAuthService',
    'CredExMemberService',
    'CredExOffersService',
    'BaseCredExService',

    # Configuration
    'CredExConfig',
    'CredExEndpoints',

    # Exceptions
    'CredExServiceError',
    'APIError',
    'AuthenticationError',
    'ConfigurationError',
    'InvalidCredExOfferError',
    'InvalidHandleError',
    'MemberNotFoundError',
    'NetworkError',
    'ResourceNotFoundError',
    'ValidationError',

    # Factory functions
    'create_service',
    'create_from_config',
]
