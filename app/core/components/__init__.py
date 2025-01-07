"""Component system

This package provides the component system with:
- Base component interfaces
- Input components
- Login components
- Component registry
"""

from .login import LoginApiCall
from .base import Component, InputComponent
from .greeting import Greeting
from .input import AmountInput, ConfirmInput, HandleInput, SelectInput
from .registration import (FirstNameInput, LastNameInput, OnBoardMemberApiCall,
                           RegistrationWelcome)
from .registry import ComponentRegistry, create_component

__all__ = [
    # Base interfaces
    "Component",
    "InputComponent",

    # Member components
    "LoginApiCall",
    "RegistrationWelcome",
    "FirstNameInput",
    "LastNameInput",
    "OnBoardMemberApiCall",

    # Input components
    "AmountInput",
    "HandleInput",
    "SelectInput",
    "ConfirmInput",

    # Output components
    "Greeting",

    # Registry
    "ComponentRegistry",
    "create_component"
]
