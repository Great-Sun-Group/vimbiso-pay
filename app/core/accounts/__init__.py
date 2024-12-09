"""Account service package

This package provides account management functionality with:
- Clear service interfaces
- Type definitions
- Base implementation
- CredEx-specific implementation
"""

from .interface import AccountServiceInterface
from .types import (
    Account,
    AccountMember,
    AccountInvite,
    AccountRole,
    AccountSettings,
    AccountType,
    AccountStatus,
    AccountUpdateResult,
    AccountMemberResult,
    AccountInviteResult,
)
from .exceptions import (
    AccountError,
    AccountValidationError,
    InvalidAccountTypeError,
    InvalidAccountStatusError,
    InvalidAccountRoleError,
    AccountNotFoundError,
    AccountMemberNotFoundError,
    AccountPermissionError,
    AccountInviteError,
    DuplicateAccountError,
    AccountSettingsError,
    AccountStateError,
)
from .base import BaseAccountService
from .credex import CredexAccountService


def create_account_service(service_type: str = "credex", **kwargs) -> AccountServiceInterface:
    """Create an account service instance

    Args:
        service_type: Type of account service to create
        **kwargs: Additional arguments passed to service constructor

    Returns:
        Account service instance

    Raises:
        ValueError: If service_type is not supported
    """
    if service_type == "credex":
        if "api_client" not in kwargs:
            raise ValueError("CredEx service requires api_client")
        return CredexAccountService(api_client=kwargs["api_client"])

    raise ValueError(f"Unsupported account service type: {service_type}")


__all__ = [
    "AccountServiceInterface",
    "Account",
    "AccountMember",
    "AccountInvite",
    "AccountRole",
    "AccountSettings",
    "AccountType",
    "AccountStatus",
    "AccountUpdateResult",
    "AccountMemberResult",
    "AccountInviteResult",
    "AccountError",
    "AccountValidationError",
    "InvalidAccountTypeError",
    "InvalidAccountStatusError",
    "InvalidAccountRoleError",
    "AccountNotFoundError",
    "AccountMemberNotFoundError",
    "AccountPermissionError",
    "AccountInviteError",
    "DuplicateAccountError",
    "AccountSettingsError",
    "AccountStateError",
    "BaseAccountService",
    "CredexAccountService",
    "create_account_service",
]
