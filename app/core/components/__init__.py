"""Component system

This package provides the component system with:
- Base component interfaces
- Input components
- Auth components
- Component registry
"""

from .auth import LoginCompleteHandler, LoginHandler
from .base import Component, InputComponent
from .input import AmountInput, ConfirmInput, HandleInput, SelectInput
from .registration import (
    FirstNameInput, LastNameInput, OnBoardMember, RegistrationWelcome
)
from .registry import ComponentRegistry, create_component

__all__ = [
    # Base interfaces
    "Component",
    "InputComponent",

    # Auth components
    "LoginHandler",
    "LoginCompleteHandler",

    # Input components
    "AmountInput",
    "HandleInput",
    "SelectInput",
    "ConfirmInput",

    # Registration components
    "RegistrationWelcome",
    "FirstNameInput",
    "LastNameInput",
    "OnBoardMember",

    # Registry
    "ComponentRegistry",
    "create_component"
]
