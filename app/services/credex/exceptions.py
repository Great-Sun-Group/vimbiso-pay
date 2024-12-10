class CredExServiceError(Exception):
    """Base exception for CredEx service errors"""
    pass


class AuthenticationError(CredExServiceError):
    """Raised when authentication fails"""
    pass


class APIError(CredExServiceError):
    """Raised when the API returns an error"""
    pass


class ValidationError(CredExServiceError):
    """Raised when request validation fails"""
    pass


class NetworkError(CredExServiceError):
    """Raised when network communication fails"""
    pass


class ConfigurationError(CredExServiceError):
    """Raised when service configuration is invalid"""
    pass


class ResourceNotFoundError(CredExServiceError):
    """Raised when a requested resource is not found"""
    pass


class MemberNotFoundError(ResourceNotFoundError):
    """Raised when a member is not found"""
    pass


class InvalidCredExOfferError(ValidationError):
    """Raised when a CredEx offer is invalid"""
    pass


class InvalidHandleError(ValidationError):
    """Raised when a handle is invalid"""
    pass
