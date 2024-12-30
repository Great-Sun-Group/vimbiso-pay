"""CredEx Service Package

This package provides a comprehensive interface for interacting with the CredEx API.
It handles authentication, member management, and CredEx offer operations.
"""

from .auth import login, refresh_token, register_member
from .base import make_credex_request
from .config import CredExConfig, CredExEndpoints
from .exceptions import (APIError, AuthenticationError, ConfigurationError,
                         CredExServiceError, InvalidCredExOfferError,
                         InvalidHandleError, MemberNotFoundError, NetworkError,
                         ResourceNotFoundError, ValidationError)
from .member import (get_member_accounts, refresh_member_info,
                     validate_account_handle)
from .offers import (accept_bulk_credex, accept_credex, cancel_credex,
                     confirm_credex, decline_credex, get_credex, get_ledger,
                     offer_credex)

__all__ = [
    # Auth functions
    'login',
    'register_member',
    'refresh_token',

    # Base functions
    'make_credex_request',

    # Member functions
    'validate_account_handle',
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
