class TransactionError(Exception):
    """Base class for transaction exceptions"""
    pass


class TransactionValidationError(TransactionError):
    """Raised when transaction validation fails"""
    pass


class InvalidTransactionTypeError(TransactionError):
    """Raised when an invalid transaction type is specified"""
    pass


class InvalidAccountError(TransactionError):
    """Raised when an invalid account is specified"""
    pass


class TransactionProcessingError(TransactionError):
    """Raised when transaction processing fails"""
    pass


class InvalidTransactionCommandError(TransactionError):
    """Raised when an invalid transaction command is provided"""
    pass


class TransactionAuthorizationError(TransactionError):
    """Raised when transaction authorization fails"""
    pass
