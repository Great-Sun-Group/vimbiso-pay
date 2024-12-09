class StateServiceError(Exception):
    """Base exception for state service errors"""
    pass


class StateNotFoundError(StateServiceError):
    """Raised when state cannot be found for a user"""
    pass


class InvalidStateError(StateServiceError):
    """Raised when state data is invalid"""
    pass


class InvalidStageError(StateServiceError):
    """Raised when an invalid stage is provided"""
    pass


class InvalidOptionError(StateServiceError):
    """Raised when an invalid option is provided"""
    pass


class InvalidUserError(StateServiceError):
    """Raised when an invalid user ID is provided"""
    pass
