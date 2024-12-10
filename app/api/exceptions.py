"""
Custom exceptions for webhook handling.
Defines specific exceptions that can occur during webhook processing.
"""
from typing import Optional, Any, Dict


class WebhookError(Exception):
    """Base exception for webhook-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class WebhookValidationError(WebhookError):
    """Raised when webhook payload fails validation."""

    def __init__(self, message: str, validation_errors: Optional[Dict[str, Any]] = None):
        super().__init__(message, details={"validation_errors": validation_errors or {}})


class WebhookSignatureError(WebhookError):
    """Raised when webhook signature validation fails."""

    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(message, details={"error_type": "signature_validation"})


class WebhookTypeError(WebhookError):
    """Raised when webhook type is not supported."""

    def __init__(self, webhook_type: str):
        message = f"Unsupported webhook type: {webhook_type}"
        super().__init__(message, details={"webhook_type": webhook_type})


class WebhookProcessingError(WebhookError):
    """Raised when there's an error processing the webhook."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        details = {
            "error_type": "processing_error",
            "original_error": str(original_error) if original_error else None
        }
        super().__init__(message, details=details)


class APIError(Exception):
    """Base exception for API-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Raised when API request validation fails."""

    def __init__(self, message: str, validation_errors: Optional[Dict[str, Any]] = None):
        super().__init__(message, details={"validation_errors": validation_errors or {}})


class AuthenticationError(APIError):
    """Raised when API authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, details={"error_type": "authentication"})


class AuthorizationError(APIError):
    """Raised when API authorization fails."""

    def __init__(self, message: str = "Authorization failed"):
        super().__init__(message, details={"error_type": "authorization"})
