"""Flow registry

This module provides central flow type management.
All flows must be registered here to be used in the system.
"""

from datetime import datetime
from typing import Dict, List

from core.utils.exceptions import FlowException


class FlowRegistry:
    """Central flow type management"""

    # Common flow configurations
    COMMON_FLOWS = {
        "action": {
            "steps": ["select", "confirm"],
            "components": {
                "select": "SelectInput",
                "confirm": "ConfirmInput"
            }
        }
    }

    # Flow type definitions with metadata
    FLOWS: Dict[str, Dict] = {
        # Member flows
        "member_registration": {
            "handler_type": "member",
            "steps": ["welcome", "firstname", "lastname", "complete"],
            "components": {
                "welcome": "RegistrationWelcome",
                "firstname": "FirstNameInput",
                "lastname": "LastNameInput",
                "complete": "RegistrationComplete"
            }
        },
        "member_upgrade": {
            "handler_type": "member",
            "steps": ["confirm", "complete"],
            "components": {
                "confirm": "UpgradeConfirm",
                "complete": "UpgradeComplete"
            }
        },
        "member_auth": {
            "handler_type": "member",
            "steps": ["greeting", "login", "login_complete"],
            "components": {
                "greeting": "Greeting",
                "login": "LoginHandler",
                "login_complete": "LoginCompleteHandler"
            }
        },

        # Account flows
        "account_dashboard": {
            "handler_type": "account",
            "steps": ["display"],
            "components": {
                "display": "AccountDashboard"
            }
        },
        "account_ledger": {
            "handler_type": "account",
            "steps": ["select", "display"],
            "components": {
                "select": "AccountSelect",
                "display": "LedgerDisplay"
            }
        },

        # Credex flows with metadata
        "credex_offer": {
            "handler_type": "credex",
            "flow_type": "offer",
            "steps": ["amount", "handle", "confirm"],
            "components": {
                "amount": "AmountInput",
                "handle": "HandleInput",
                "confirm": "ConfirmInput"
            }
        },
        # Action flows use common configuration
        "credex_accept": {
            "handler_type": "credex",
            "flow_type": "action",
            "action_type": "accept",
            **COMMON_FLOWS["action"]
        },
        "credex_decline": {
            "handler_type": "credex",
            "flow_type": "action",
            "action_type": "decline",
            **COMMON_FLOWS["action"]
        },
        "credex_cancel": {
            "handler_type": "credex",
            "flow_type": "action",
            "action_type": "cancel",
            **COMMON_FLOWS["action"]
        }
    }

    # Valid action types
    ACTION_TYPES = {"accept", "decline", "cancel"}

    @classmethod
    def get_flow_config(cls, flow_type: str) -> Dict:
        """Get flow configuration with standardized validation tracking

        Args:
            flow_type: Flow type identifier

        Returns:
            Dict with flow configuration and validation state

        Raises:
            FlowException: If flow type invalid or action type invalid
        """
        # Create validation state
        validation_state = {
            "in_progress": True,
            "attempts": 0,  # Registry operations don't track attempts
            "operation": "get_flow_config",
            "component": "flow_registry",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            if flow_type not in cls.FLOWS:
                validation_state.update({
                    "in_progress": False,
                    "error": {
                        "message": f"Invalid flow type: {flow_type}",
                        "details": {"flow_type": flow_type},
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
                raise FlowException(
                    message=f"Invalid flow type: {flow_type}",
                    step="init",
                    action="get_config",
                    data={"flow_type": flow_type, "validation": validation_state}
                )

            config = cls.FLOWS[flow_type]

            # Validate action type if present
            if config.get("flow_type") == "action":
                action_type = config.get("action_type")
                if not action_type or action_type not in cls.ACTION_TYPES:
                    validation_state.update({
                        "in_progress": False,
                        "error": {
                            "message": f"Invalid action type: {action_type}",
                            "details": {
                                "flow_type": flow_type,
                                "action_type": action_type
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
                    raise FlowException(
                        message=f"Invalid action type: {action_type}",
                        step="init",
                        action="get_config",
                        data={
                            "flow_type": flow_type,
                            "action_type": action_type,
                            "validation": validation_state
                        }
                    )

            # Update validation state for success
            validation_state.update({
                "in_progress": False,
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Add validation state and metadata to config
            return {
                **config,
                "_validation": validation_state,
                "_metadata": {
                    "retrieved_at": datetime.utcnow().isoformat()
                }
            }

        except FlowException:
            raise
        except Exception as e:
            validation_state.update({
                "in_progress": False,
                "error": {
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            raise FlowException(
                message=f"Failed to get flow config: {str(e)}",
                step="init",
                action="get_config",
                data={"flow_type": flow_type, "validation": validation_state}
            )

    @classmethod
    def get_flow_steps(cls, flow_type: str) -> List[str]:
        """Get flow step sequence with validation"""
        config = cls.get_flow_config(flow_type)

        # Get steps from common flow if needed
        if config.get("flow_type") in cls.COMMON_FLOWS:
            return cls.COMMON_FLOWS[config["flow_type"]]["steps"]

        return config["steps"]

    @classmethod
    def get_step_component(cls, flow_type: str, step: str) -> str:
        """Get component type for step with validation"""
        config = cls.get_flow_config(flow_type)

        # Get components from common flow if needed
        if config.get("flow_type") in cls.COMMON_FLOWS:
            components = cls.COMMON_FLOWS[config["flow_type"]]["components"]
        else:
            components = config["components"]

        if step not in components:
            raise FlowException(
                message=f"Invalid step: {step}",
                step=step,
                action="get_component",
                data={"flow_type": flow_type}
            )

        return components[step]

    @classmethod
    def validate_flow_step(cls, flow_type: str, step: str) -> None:
        """Validate flow step with standardized validation tracking"""
        # Create validation state
        validation_state = {
            "in_progress": True,
            "attempts": 0,  # Registry operations don't track attempts
            "operation": "validate_flow_step",
            "component": "flow_registry",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            config = cls.get_flow_config(flow_type)

            # Get steps from common flow if needed
            if config.get("flow_type") in cls.COMMON_FLOWS:
                steps = cls.COMMON_FLOWS[config["flow_type"]]["steps"]
            else:
                steps = config["steps"]

            if step not in steps:
                validation_state.update({
                    "in_progress": False,
                    "error": {
                        "message": f"Invalid step {step} for flow {flow_type}",
                        "details": {
                            "flow_type": flow_type,
                            "step": step,
                            "valid_steps": steps
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
                raise FlowException(
                    message=f"Invalid step {step} for flow {flow_type}",
                    step=step,
                    action="validate",
                    data={
                        "flow_type": flow_type,
                        "valid_steps": steps,
                        "validation": validation_state
                    }
                )

            # Update validation state for success
            validation_state.update({
                "in_progress": False,
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            })

        except FlowException:
            raise
        except Exception as e:
            validation_state.update({
                "in_progress": False,
                "error": {
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            raise FlowException(
                message=f"Failed to validate flow step: {str(e)}",
                step=step,
                action="validate",
                data={
                    "flow_type": flow_type,
                    "validation": validation_state
                }
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
