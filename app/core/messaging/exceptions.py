class MessagingError(Exception):
    """Base exception for messaging errors"""
    pass


class MessageValidationError(MessagingError):
    """Raised when message validation fails"""
    pass


class MessageDeliveryError(MessagingError):
    """Raised when message delivery fails"""
    pass


class MessageTemplateError(MessagingError):
    """Raised when there's an error with message templates"""
    pass


class MessageHandlerError(MessagingError):
    """Raised when message handling fails"""
    pass


class InvalidMessageTypeError(MessagingError):
    """Raised when an invalid message type is encountered"""
    pass


class InvalidRecipientError(MessagingError):
    """Raised when recipient information is invalid"""
    pass


class MessageRateLimitError(MessagingError):
    """Raised when message rate limits are exceeded"""
    pass


class MessageFormatError(MessagingError):
    """Raised when message formatting fails"""
    pass


class TemplateNotFoundError(MessageTemplateError):
    """Raised when a requested template is not found"""
    pass


class TemplateValidationError(MessageTemplateError):
    """Raised when template validation fails"""
    pass
