"""Flow registry

This module provides central flow type management.
All flows must be registered here to be used in the system.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

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
        "member_onboard": {
            "handler_type": "member",
            "steps": ["welcome", "firstname", "lastname", "registration_attempt", "dashboard"],
            "components": {
                "welcome": "RegistrationWelcome",
                "firstname": "FirstNameInput",
                "lastname": "LastNameInput",
                "greet": "Greeting",
                "onboard_member": "OnBoardMemberApiCall"
            },
            "auto_progress": {
                "greet": True,
                "onboard_member": True
            },
            "exit_conditions": {
                "success": "account_dashboard",  # On successful registration
                "error": None  # Stay in flow on error
            }
        },
        "member_upgrade": {
            "handler_type": "member",
            "steps": ["confirm", "complete"],
            "components": {
                "confirm": "UpgradeConfirm",
                "complete": "UpgradeComplete"
            },
            "exit_conditions": {
                "success": "account_dashboard",  # Return to dashboard after upgrade
                "error": None  # Stay in flow on error
            }
        },
        "member_login": {
            "handler_type": "member",
            "steps": ["greet", "login"],
            "components": {
                "greet": "Greeting",
                "login": "LoginApiCall"
            },
            "auto_progress": {
                "greet": True,  # Show greeting then auto-progress
                "login": True  # Make API call then check result
            },
            "exit_conditions": {
                "success": "account_dashboard",  # On successful login
                "not_member": "member_onboard",
                "error": None  # Stay in flow on error
            }
        },

        # Account flows
        "account_dashboard": {
            "handler_type": "account",
            "steps": ["display"],
            "components": {
                "display": "AccountDashboard"
            },
            "auto_progress": {
                "display": True  # Auto-progress dashboard display
            },
            "exit_conditions": {
                "success": None,  # End flow after display
                "error": None  # Stay in flow on error
            }
        },
        "account_ledger": {
            "handler_type": "account",
            "steps": ["select", "display"],
            "components": {
                "select": "AccountSelect",
                "display": "LedgerDisplay"
            },
            "exit_conditions": {
                "success": "account_dashboard",  # Return to dashboard after viewing
                "error": None  # Stay in flow on error
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
            },
            "exit_conditions": {
                "success": "account_dashboard",  # Return to dashboard after offer
                "error": None  # Stay in flow on error
            }
        },
        # Action flows use common configuration
        "credex_accept": {
            "handler_type": "credex",
            "flow_type": "action",
            "action_type": "accept",
            **COMMON_FLOWS["action"],
            "exit_conditions": {
                "success": "account_dashboard",  # Return to dashboard after accept
                "error": None  # Stay in flow on error
            }
        },
        "credex_decline": {
            "handler_type": "credex",
            "flow_type": "action",
            "action_type": "decline",
            **COMMON_FLOWS["action"],
            "exit_conditions": {
                "success": "account_dashboard",  # Return to dashboard after decline
                "error": None  # Stay in flow on error
            }
        },
        "credex_cancel": {
            "handler_type": "credex",
            "flow_type": "action",
            "action_type": "cancel",
            **COMMON_FLOWS["action"],
            "exit_conditions": {
                "success": "account_dashboard",  # Return to dashboard after cancel
                "error": None  # Stay in flow on error
            }
        }
    }

    # Valid action types
    ACTION_TYPES = {"accept", "decline", "cancel"}

    # Valid exit conditions
    EXIT_CONDITIONS = {"success", "error", "not_member"}

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
    def get_step_component(cls, flow_type: str, step: str) -> Union[str, List[str]]:
        """Get component type(s) for step with validation

        Returns either a single component type string or a list of component types
        if multiple components are configured for the step.
        """
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
    def should_auto_progress(cls, flow_type: str, step: str) -> bool:
        """Check if step should auto-progress without user input

        Args:
            flow_type: Flow type identifier
            step: Current step

        Returns:
            bool: True if step should auto-progress, False otherwise
        """
        config = cls.get_flow_config(flow_type)
        auto_progress = config.get("auto_progress", {})
        return auto_progress.get(step, False)

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

    @classmethod
    def get_exit_flow(cls, flow_type: str, condition: str) -> Optional[str]:
        """Get next flow based on exit condition

        Args:
            flow_type: Current flow type
            condition: Exit condition (success, error, not_member)

        Returns:
            Optional[str]: Next flow type or None to stay in current flow

        Raises:
            FlowException: If condition invalid
        """
        if condition not in cls.EXIT_CONDITIONS:
            raise FlowException(
                message=f"Invalid exit condition: {condition}",
                step="exit",
                action="get_next_flow",
                data={"flow_type": flow_type, "condition": condition}
            )

        config = cls.get_flow_config(flow_type)
        exit_conditions = config.get("exit_conditions", {})
        return exit_conditions.get(condition)
