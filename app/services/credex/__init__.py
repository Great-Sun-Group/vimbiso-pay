"""CredEx Service Package

This package provides a comprehensive interface for interacting with the CredEx API.
It handles authentication, member management, and CredEx offer operations.
"""

from .auth import (
    login,
    register_member,
    refresh_token,
    validate_member_data,
    extract_token,
)
from .base import (
    make_credex_request,
    validate_response,
    handle_error_response,
    extract_error_message,
)
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
from .member import (
    get_dashboard,
    validate_handle,
    refresh_member_info,
    get_member_accounts,
)
from .offers import (
    offer_credex,
    confirm_credex,
    accept_credex,
    accept_bulk_credex,
    decline_credex,
    cancel_credex,
    get_credex,
    get_ledger,
)


__all__ = [
    # Auth functions
    'login',
    'register_member',
    'refresh_token',
    'validate_member_data',
    'extract_token',

    # Base functions
    'make_credex_request',
    'validate_response',
    'handle_error_response',
    'extract_error_message',

    # Member functions
    'get_dashboard',
    'validate_handle',
    'refresh_member_info',
    'get_member_accounts',

    # Offer functions
    'offer_credex',
    'confirm_credex',
    'accept_credex',
    'accept_bulk_credex',
    'decline_credex',
    'cancel_credex',
    'get_credex',
    'get_ledger',

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
]
