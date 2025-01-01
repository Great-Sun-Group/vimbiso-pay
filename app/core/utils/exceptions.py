from typing import Any, Dict


class CredExCoreException(Exception):
    """Base exception for CredEx Core"""
    pass


class InvalidInputException(CredExCoreException):
    """Exception raised for invalid user input"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class APIException(CredExCoreException):
    """Exception raised for API-related errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class StateException(CredExCoreException):
    """Exception raised for state-related errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ActionHandlerException(CredExCoreException):
    """Exception raised for errors in action handlers"""
    def __init__(self, message: str, action: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.action = action
        self.details = details or {}
        super().__init__(message)


class ConfigurationException(CredExCoreException):
    """Exception raised for configuration-related errors"""
    def __init__(self, message: str, subtype: str = None):
        self.message = message
        self.subtype = subtype
        super().__init__(message)
