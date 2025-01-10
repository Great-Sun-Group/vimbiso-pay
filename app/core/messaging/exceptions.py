from typing import Any, Dict, Optional

from core.error.exceptions import BaseException


class MessagingError(BaseException):
    """Base exception for messaging errors"""
    def __init__(
        self,
        message: str,
        code: str,
        service: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, {
            "code": code,
            "service": service,
            "action": action,
            **(details or {})
        })


class MessageValidationError(MessagingError):
    """Raised when message validation fails"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        validation_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            service=service,
            action=action,
            details={"validation": validation_details}
        )


class MessageDeliveryError(MessagingError):
    """Raised when message delivery fails"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        delivery_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            code="DELIVERY_ERROR",
            service=service,
            action=action,
            details={"delivery": delivery_details}
        )


class MessageTemplateError(MessagingError):
    """Raised when there's an error with message templates"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        template_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            code="TEMPLATE_ERROR",
            service=service,
            action=action,
            details={"template": template_details}
        )


class MessageHandlerError(MessagingError):
    """Raised when message handling fails"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        handler_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            code="HANDLER_ERROR",
            service=service,
            action=action,
            details={"handler": handler_details}
        )


class InvalidMessageTypeError(MessageValidationError):
    """Raised when an invalid message type is encountered"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        type_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            service=service,
            action=action,
            validation_details={"type": type_details}
        )


class InvalidRecipientError(MessageValidationError):
    """Raised when recipient information is invalid"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        recipient_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            service=service,
            action=action,
            validation_details={"recipient": recipient_details}
        )


class MessageRateLimitError(MessageDeliveryError):
    """Raised when message rate limits are exceeded"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        rate_limit_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            service=service,
            action=action,
            delivery_details={"rate_limit": rate_limit_details}
        )


class MessageFormatError(MessageValidationError):
    """Raised when message formatting fails"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        format_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            service=service,
            action=action,
            validation_details={"format": format_details}
        )


class TemplateNotFoundError(MessageTemplateError):
    """Raised when a requested template is not found"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        template_name: str
    ):
        super().__init__(
            message=message,
            service=service,
            action=action,
            template_details={"name": template_name}
        )


class TemplateValidationError(MessageTemplateError):
    """Raised when template validation fails"""
    def __init__(
        self,
        message: str,
        service: str,
        action: str,
        validation_details: Dict[str, Any]
    ):
        super().__init__(
            message=message,
            service=service,
            action=action,
            template_details={"validation": validation_details}
        )
