class AccountError(Exception):
    """Base class for account exceptions"""
    pass


class AccountValidationError(AccountError):
    """Raised when account validation fails"""
    pass


class InvalidAccountTypeError(AccountError):
    """Raised when an invalid account type is specified"""
    pass


class InvalidAccountStatusError(AccountError):
    """Raised when an invalid account status is specified"""
    pass


class InvalidAccountRoleError(AccountError):
    """Raised when an invalid account role is specified"""
    pass


class AccountNotFoundError(AccountError):
    """Raised when an account cannot be found"""
    pass


class AccountMemberNotFoundError(AccountError):
    """Raised when an account member cannot be found"""
    pass


class AccountPermissionError(AccountError):
    """Raised when an operation is not permitted"""
    pass


class AccountInviteError(AccountError):
    """Raised when there is an error with account invites"""
    pass


class DuplicateAccountError(AccountError):
    """Raised when attempting to create a duplicate account"""
    pass


class AccountSettingsError(AccountError):
    """Raised when there is an error with account settings"""
    pass


class AccountStateError(AccountError):
    """Raised when an operation is not valid for the current account state"""
    pass
