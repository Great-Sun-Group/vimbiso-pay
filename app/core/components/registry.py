"""Component registry

This module provides central component management and creation.
All components must be registered here to be used in flows.
"""

from typing import Dict, Type

from .base import Component
from .auth import LoginHandler, LoginCompleteHandler, DashboardDisplay
from .input import AmountInput, ConfirmInput, HandleInput, SelectInput, ButtonInput
from .registration import FirstNameInput, LastNameInput, RegistrationComplete
from .upgrade import UpgradeConfirm, UpgradeComplete


class ComponentRegistry:
    """Central component management"""

    # Component type definitions
    COMPONENTS: Dict[str, Dict] = {
        # Auth components
        "LoginHandler": {
            "type": "auth",
            "class": LoginHandler,
            "validates": ["login"],
            "converts_to": ["auth_response"]
        },
        "LoginCompleteHandler": {
            "type": "auth",
            "class": LoginCompleteHandler,
            "validates": ["auth_response"],
            "converts_to": ["member_data", "accounts"]
        },
        "DashboardDisplay": {
            "type": "display",
            "class": DashboardDisplay,
            "validates": ["member_id"],
            "converts_to": ["dashboard_data"]
        },

        # Registration components
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
        "RegistrationComplete": {
            "type": "registration",
            "class": RegistrationComplete,
            "validates": ["registration_response"],
            "converts_to": ["member_data"]
        },

        # Upgrade components
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

        # Input components
        "ButtonInput": {
            "type": "input",
            "class": ButtonInput,
            "validates": ["button_input"],
            "converts_to": ["button_id"]
        },
        "AmountInput": {
            "type": "input",
            "class": AmountInput,
            "validates": ["amount"],
            "converts_to": ["amount"]
        },
        "HandleInput": {
            "type": "input",
            "class": HandleInput,
            "validates": ["handle"],
            "converts_to": ["handle"]
        },
        "SelectInput": {
            "type": "input",
            "class": SelectInput,
            "validates": ["selection"],
            "converts_to": ["selected_id"]
        },
        "ConfirmInput": {
            "type": "input",
            "class": ConfirmInput,
            "validates": ["confirmation"],
            "converts_to": ["confirmed"]
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
