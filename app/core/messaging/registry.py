"""Flow registry

This module provides central flow type management.
All flows must be registered here to be used in the system.
"""

from typing import Dict, List

from core.utils.exceptions import FlowException


class FlowRegistry:
    """Central flow type management"""

    # Flow type definitions
    FLOWS: Dict[str, Dict] = {
        # Authentication flows
        "auth": {
            "steps": ["login", "login_complete"],
            "components": {
                "login": "LoginHandler",
                "login_complete": "LoginCompleteHandler"
            }
        },
        "dashboard": {
            "steps": ["main"],
            "components": {
                "main": "DashboardDisplay"
            }
        },
        # Transaction flows
        "offer": {
            "steps": ["amount", "handle", "confirm"],
            "components": {
                "amount": "AmountInput",
                "handle": "HandleInput",
                "confirm": "ConfirmInput"
            }
        },
        "accept": {
            "steps": ["select", "confirm"],
            "components": {
                "select": "SelectInput",
                "confirm": "ConfirmInput"
            }
        },
        "decline": {
            "steps": ["select", "confirm"],
            "components": {
                "select": "SelectInput",
                "confirm": "ConfirmInput"
            }
        },
        "cancel": {
            "steps": ["select", "confirm"],
            "components": {
                "select": "SelectInput",
                "confirm": "ConfirmInput"
            }
        }
    }

    @classmethod
    def get_flow_config(cls, flow_type: str) -> Dict:
        """Get flow configuration"""
        if flow_type not in cls.FLOWS:
            raise FlowException(
                message=f"Invalid flow type: {flow_type}",
                step="init",
                action="get_config",
                data={"flow_type": flow_type}
            )
        return cls.FLOWS[flow_type]

    @classmethod
    def get_flow_steps(cls, flow_type: str) -> List[str]:
        """Get flow step sequence"""
        config = cls.get_flow_config(flow_type)
        return config["steps"]

    @classmethod
    def get_step_component(cls, flow_type: str, step: str) -> str:
        """Get component type for step"""
        config = cls.get_flow_config(flow_type)
        if step not in config["components"]:
            raise FlowException(
                message=f"Invalid step: {step}",
                step=step,
                action="get_component",
                data={"flow_type": flow_type}
            )
        return config["components"][step]

    @classmethod
    def validate_flow_step(cls, flow_type: str, step: str) -> None:
        """Validate flow step"""
        config = cls.get_flow_config(flow_type)
        if step not in config["steps"]:
            raise FlowException(
                message=f"Invalid step {step} for flow {flow_type}",
                step=step,
                action="validate",
                data={"flow_type": flow_type}
            )

    @classmethod
    def get_next_step(cls, flow_type: str, current_step: str) -> str:
        """Get next step in flow"""
        steps = cls.get_flow_steps(flow_type)
        try:
            current_index = steps.index(current_step)
            if current_index < len(steps) - 1:
                return steps[current_index + 1]
            return "complete"
        except ValueError:
            raise FlowException(
                message=f"Invalid step {current_step} for flow {flow_type}",
                step=current_step,
                action="get_next",
                data={"flow_type": flow_type}
            )
