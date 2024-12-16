"""State service exceptions with simplified hierarchy"""
from typing import Optional


class StateError(Exception):
    """Base exception for all state-related errors"""
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class StateValidationError(StateError):
    """Raised for all state validation errors"""
    pass


class StateOperationError(StateError):
    """Raised for all state operation errors"""
    pass
