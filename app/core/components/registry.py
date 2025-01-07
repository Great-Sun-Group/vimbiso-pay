"""Component registry

This module provides central component management and creation.
All components must be registered here to be used in flows.
"""

from typing import Dict, Type

from .base import Component
from .account import AccountDashboard, AccountSelect, LedgerDisplay
from .greeting import Greeting
from .login import LoginApiCall
from .input import AmountInput, ConfirmInput, HandleInput, SelectInput, ButtonInput
from .registration import (
    FirstNameInput, LastNameInput, OnBoardMemberApiCall, RegistrationWelcome
)
from .upgrade import UpgradeConfirm, UpgradeComplete


class ComponentRegistry:
    """Central component management"""

    # Component type definitions matching service structure
    COMPONENTS: Dict[str, Dict] = {
        # Greeting components
        "Greeting": {
            "type": "greeting",
            "class": Greeting,
            "validates": ["greet"],
            "converts_to": ["message"]
        },

        # Member components
        "LoginApiCall": {
            "type": "login",
            "class": LoginApiCall,
            "validates": ["login"],
            "converts_to": ["auth_data", "member_data"]
        },

        # Member registration components
        "RegistrationWelcome": {
            "type": "registration",
            "class": RegistrationWelcome,
            "validates": ["welcome_response"],
            "converts_to": ["registration_start"]
        },
        "FirstNameInput": {
            "type": "registration",
            "class": FirstNameInput,
            "validates": ["firstname"],
            "converts_to": ["verified_firstname"]
        },
        "LastNameInput": {
            "type": "registration",
            "class": LastNameInput,
            "validates": ["lastname"],
            "converts_to": ["verified_lastname"]
        },
        "OnBoardMemberApiCall": {
            "type": "registration",
            "class": OnBoardMemberApiCall,
            "validates": ["onboarding_response"],
            "converts_to": ["member_data"]
        },

        # Member upgrade components
        "UpgradeConfirm": {
            "type": "upgrade",
            "class": UpgradeConfirm,
            "validates": ["upgrade_confirmation"],
            "converts_to": ["verified_upgrade"]
        },
        "UpgradeComplete": {
            "type": "upgrade",
            "class": UpgradeComplete,
            "validates": ["upgrade_response"],
            "converts_to": ["upgrade_data"]
        },

        # Account components
        "AccountDashboard": {
            "type": "account",
            "class": AccountDashboard,
            "validates": ["account_data"],
            "converts_to": ["dashboard_display"]
        },
        "AccountSelect": {
            "type": "account",
            "class": AccountSelect,
            "validates": ["account_id"],
            "converts_to": ["verified_account"]
        },
        "LedgerDisplay": {
            "type": "account",
            "class": LedgerDisplay,
            "validates": ["ledger_data"],
            "converts_to": ["verified_ledger"]
        },

        # Common input components
        "ButtonInput": {
            "type": "input",
            "class": ButtonInput,
            "validates": ["button_input"],
            "converts_to": ["button_id"]
        },
        "AmountInput": {
            "type": "input",
            "class": AmountInput,
            "validates": ["amount", "denom"],
            "converts_to": ["verified_amount"]
        },
        "HandleInput": {
            "type": "input",
            "class": HandleInput,
            "validates": ["handle"],
            "converts_to": ["verified_handle"]
        },
        "SelectInput": {
            "type": "input",
            "class": SelectInput,
            "validates": ["selection"],
            "converts_to": ["verified_selection"]
        },
        "ConfirmInput": {
            "type": "input",
            "class": ConfirmInput,
            "validates": ["confirmation"],
            "converts_to": ["verified_confirmation"]
        }
    }

    @classmethod
    def get_component_class(cls, component_type: str) -> Type[Component]:
        """Get component class by type"""
        if component_type not in cls.COMPONENTS:
            raise ValueError(f"Unknown component type: {component_type}")
        return cls.COMPONENTS[component_type]["class"]

    @classmethod
    def create_component(cls, component_type: str, **kwargs) -> Component:
        """Create component instance"""
        component_class = cls.get_component_class(component_type)
        return component_class(**kwargs)

    @classmethod
    def get_component_info(cls, component_type: str) -> Dict:
        """Get component type information"""
        if component_type not in cls.COMPONENTS:
            raise ValueError(f"Unknown component type: {component_type}")
        return cls.COMPONENTS[component_type]


def create_component(component_type: str, **kwargs) -> Component:
    """Create component instance

    This is the main factory function for creating components.
    All component creation should go through here.

    Args:
        component_type: Type of component to create
        **kwargs: Component-specific arguments

    Returns:
        Component instance

    Raises:
        ValueError: If component type unknown
    """
    return ComponentRegistry.create_component(component_type, **kwargs)
