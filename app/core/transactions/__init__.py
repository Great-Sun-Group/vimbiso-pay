"""Transaction service package

This package provides transaction handling functionality with:
- Clear service interfaces
- Type definitions
- Base implementation
- CredEx-specific implementation
"""

from .interface import TransactionServiceInterface
from .types import (
    Account,
    Transaction,
    TransactionOffer,
    TransactionResult,
    TransactionStatus,
    TransactionType,
)
from .exceptions import (
    TransactionError,
    TransactionValidationError,
    InvalidTransactionTypeError,
    InvalidAccountError,
    TransactionProcessingError,
    InvalidTransactionCommandError,
    TransactionAuthorizationError,
)
from .base import BaseTransactionService
from .credex import CredexTransactionService


def create_transaction_service(service_type: str = "credex", **kwargs) -> TransactionServiceInterface:
    """Create a transaction service instance

    Args:
        service_type: Type of transaction service to create
        **kwargs: Additional arguments passed to service constructor

    Returns:
        Transaction service instance

    Raises:
        ValueError: If service_type is not supported
    """
    if service_type == "credex":
        if "api_client" not in kwargs:
            raise ValueError("CredEx service requires api_client")
        return CredexTransactionService(api_client=kwargs["api_client"])

    raise ValueError(f"Unsupported transaction service type: {service_type}")


__all__ = [
    "TransactionServiceInterface",
    "Account",
    "Transaction",
    "TransactionOffer",
    "TransactionResult",
    "TransactionStatus",
    "TransactionType",
    "TransactionError",
    "TransactionValidationError",
    "InvalidTransactionTypeError",
    "InvalidAccountError",
    "TransactionProcessingError",
    "InvalidTransactionCommandError",
    "TransactionAuthorizationError",
    "BaseTransactionService",
    "CredexTransactionService",
    "create_transaction_service",
]
