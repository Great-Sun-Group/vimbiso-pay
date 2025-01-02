"""Component system

This package provides the component system with:
- Base component interfaces
- Input components
- Auth components
- Component registry
"""

from .auth import DashboardDisplay, LoginCompleteHandler, LoginHandler
from .base import Component, InputComponent
from .input import AmountInput, ConfirmInput, HandleInput, SelectInput
from .registry import ComponentRegistry, create_component

__all__ = [
    # Base interfaces
    "Component",
    "InputComponent",

    # Auth components
    "LoginHandler",
    "LoginCompleteHandler",
    "DashboardDisplay",

    # Input components
    "AmountInput",
    "HandleInput",
    "SelectInput",
    "ConfirmInput",

    # Registry
    "ComponentRegistry",
    "create_component"
]
