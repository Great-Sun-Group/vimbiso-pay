"""Core exceptions with clear error boundaries

This module defines the base exceptions used throughout the system.
Each exception maps to a specific error type with clear boundaries.
"""

from typing import Dict, Optional


class BaseException(Exception):
    """Base exception with error details"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ComponentException(BaseException):
    """Component validation errors"""
    def __init__(
        self,
        message: str,
        component: str,
        field: str,
        value: str,
        validation: Optional[Dict] = None
    ):
        details = {
            "component": component,
            "field": field,
            "value": value,
            "validation": validation
        }
        super().__init__(message, details)


class FlowException(BaseException):
    """Flow business logic errors"""
    def __init__(
        self,
        message: str,
        step: str,
        action: str,
        data: Dict
    ):
        details = {
            "step": step,
            "action": action,
            "data": data
        }
        super().__init__(message, details)


class SystemException(BaseException):
    """System technical errors"""
    def __init__(
        self,
        message: str,
        code: str,
        service: str,
        action: str
    ):
        details = {
            "code": code,
            "service": service,
            "action": action
        }
        super().__init__(message, details)


# Specific component exceptions
class ValidationException(ComponentException):
    """Input validation errors"""
    pass


class ConversionException(ComponentException):
    """Data conversion errors"""
    pass


# Specific flow exceptions
class InvalidStepException(FlowException):
    """Invalid flow step errors"""
    pass


class InvalidActionException(FlowException):
    """Invalid flow action errors"""
    pass


# Specific system exceptions
class ConfigurationException(SystemException):
    """System configuration errors"""
    pass


class ServiceException(SystemException):
    """External service errors"""
    pass
