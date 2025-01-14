"""Component Manager

This module handles the component activation and processing logic used by headquarters.py.
It provides functionality for creating, retrieving, and activating components, as well as managing
the component processing lifecycle.
"""

import logging
from typing import Optional, Tuple

from core import components
from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.state.interface import StateManagerInterface

logger = logging.getLogger(__name__)


# Cache for active component instances
_active_components = {}


def activate_component(component_type: str, state_manager: StateManagerInterface) -> ValidationResult:
    """Create or retrieve and activate a component for the current path step.

    Handles component processing:
    1. Creates new component instance or retrieves existing one if awaiting input
    2. Configures state management
    3. Returns component result

    Args:
        component_type: Component for this step (e.g. "Greeting", "LoginApiCall")
        state_manager: State manager for component configuration and validation

    Returns:
        ValidationResult: Component activation result

    Raises:
        ComponentException: If component creation or activation fails
    """
    # Get channel identifier for component cache key
    channel_id = state_manager.get_channel_id()
    cache_key = f"{channel_id}:{component_type}"

    try:
        # Check if we have an active instance awaiting input
        if state_manager.is_awaiting_input() and cache_key in _active_components:
            component = _active_components[cache_key]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Retrieved active component instance: {component.type}")
        else:
            # Create new component instance
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Creating component for step: {component_type}")

            component_class = getattr(components, component_type)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Found component class: {component_class.__name__}")

            component = component_class()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Created component instance: {component.type}")

            # Cache the new instance
            _active_components[cache_key] = component

        # Ensure state manager is set
        component.set_state_manager(state_manager)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Set state manager on component")

        # Activate component
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Activating component")
        result = component.validate(None)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Activation result: {result}")

        # Clear from cache if no longer awaiting input
        if not state_manager.is_awaiting_input():
            _active_components.pop(cache_key, None)

        return result

    except AttributeError as e:
        logger.error(f"Component not found: {component_type}")
        logger.error(f"Available components: {dir(components)}")
        raise ComponentException(
            message=f"Component not found: {component_type}",
            component=component_type,
            field="type",
            value=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to activate component: {str(e)}")
        raise ComponentException(
            message=f"Component activation failed: {str(e)}",
            component=component_type,
            field="activation",
            value=str(e)
        )


def process_component(path: str, component: str, state_manager: StateManagerInterface, depth: int = 0) -> Optional[Tuple[str, str]]:
    """Process current step and determine next step in application paths.

    Handles the complete step processing:
    1. Activates component for current step
    2. Lets component process its logic
    3. Determines next step in path

    Args:
        path: Path category (e.g. "login", "offer_secured", "account")
        component: Current step's component in the path
        state_manager: State manager for component activation and path control

    Returns:
        Optional[Tuple[str, str]]: Next step (path, component) in the current path, or None if activation failed
    """
    logger.info(f"Processing component: {path}.{component} (depth: {depth})")
    if depth > 10:  # Arbitrary limit to catch potential issues
        logger.error(f"Maximum component processing depth exceeded: {path}.{component}")
        return None
    logger.info(f"Current awaiting_input: {state_manager.is_awaiting_input()}")

    # Activate component for current step
    logger.info("Activating component...")
    result = activate_component(component, state_manager)
    logger.info(f"Activation result: {result}")
    logger.info(f"Awaiting input after activation: {state_manager.is_awaiting_input()}")

    # Handle validation failures
    if not result.valid:
        logger.error(f"Component activation failed: {result.error}")

        # Check if we should retry handle input
        if (path == "offer_secured" and
                component == "ValidateAccountApiCall" and
                isinstance(result.error, dict) and
                result.error.get("details", {}).get("retry")):
            return "offer_secured", "HandleInput"

        return None

    # Check if still awaiting input after activation
    if state_manager.is_awaiting_input():
        logger.info("Still awaiting input after activation")
        return path, component

    # Import get_next_component here to avoid circular imports
    from .headquarters import get_next_component

    # Determine next step in path
    logger.info("Getting next component...")
    next_step = get_next_component(path, component, state_manager)
    logger.info(f"Next step: {next_step}")
    logger.info(f"Final awaiting_input: {state_manager.is_awaiting_input()}")

    return next_step
