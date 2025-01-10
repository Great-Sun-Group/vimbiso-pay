"""Flow Headquarters

This module defines the core logic that manages member flows through the vimbiso-chatserver application.
It activates a component at each step, and determines the next step through branching logic.
Data management is delegated to the state manager, and action management is delegated to the components.

Components are self-contained with responsibility for their own:
- Business logic and validation
- Activation of shared utilities/helpers/services
- State access through get_state_value() for schema-validated fields
- Freedom to store any data in component_data.data dict
- State updates that must pass schema validation except for component_data.data
- Error handling

The state manager provides:
- Schema validation for all state updates except component_data.data
- Single source of truth for all state
- Clear boundaries through schema validation
- Component freedom through unvalidated data dict
- Atomic updates through Redis persistence
"""

import logging
from typing import Tuple, Optional

from core import components
from core.error.types import ValidationResult
from core.state.interface import StateManagerInterface

logger = logging.getLogger(__name__)


def activate_component(component_type: str, state_manager: StateManagerInterface) -> ValidationResult:
    """Create and activate a component for the current path step.

    Handles component processing:
    1. Creates component instance
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
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Creating component for step: {component_type}")

    # Create component for this step
    component_class = getattr(components, component_type)
    component = component_class()
    component.set_state_manager(state_manager)

    # Validate all components
    return component.validate(None)


def get_next_component(
    path: str,
    component: str,
    state_manager: StateManagerInterface
) -> Tuple[str, str]:
    """Determine next path/Component based on current path/Component completion and optional component_result.
    Handle progression through and between flows.

    Args:
        path: (e.g. "login", "offer_secured", "account")
        component: Current step's component (e.g. "AmountInput", "HandleInput", "ConfirmOffer", "CreateCredexApiCall")
        state_manager: State manager for checking awaiting_input and component_result

    Returns:
        Tuple[str, str]: Next path/Component
    """
    # Check if component is awaiting input
    if state_manager.is_awaiting_input():
        return path, component  # Stay at current step until input received

    # Get component result for branching (using new state manager API)
    component_result = state_manager.get_state_value("component_data", {}).get("component_result")

    # Branch based on current path
    match (path, component):

        # Login path
        case ("login", "Greeting"):
            return "login", "LoginApiCall"  # Check if user exists
        case ("login", "LoginApiCall"):
            if component_result == "send_dashboard":
                return "account", "AccountDashboard"  # Send account dashboard
            if component_result == "start_onboarding":
                return "onboard", "Welcome"  # Send first message in onboarding path

        # Onboard path
        case ("onboard", "Welcome"):
            return "onboard", "FirstNameInput"  # Start collecting user details
        case ("onboard", "FirstNameInput"):
            return "onboard", "LastNameInput"  # Continue with user details
        case ("onboard", "LastNameInput"):
            return "onboard", "Greeting"  # Send random greeting while API call processes
        case ("onboard", "Greeting"):
            return "onboard", "OnBoardMemberApiCall"  # Create member and account with collected details
        case ("onboard", "OnBoardMemberApiCall"):
            return "account", "AccountDashboard"  # Send account dashboard

        # Account dashboard path
        case ("account", "AccountDashboard"):
            if component_result == "offer_secured":
                return "offer_secured", "AmountInput"  # Start collecting offer details with amount/denom
            if component_result == "accept_offer":
                return "accept_offer", "OfferListDisplay"  # List pending incoming offers to accept
            if component_result == "decline_offer":
                return "decline_offer", "OfferListDisplay"  # List pending incoming offers to decline
            if component_result == "cancel_offer":
                return "cancel_offer", "OfferListDisplay"  # List pending outgoing offers to cancel
            if component_result == "view_ledger":
                return "view_ledger", "Greeting"  # Send random greeting while api call processes
            if component_result == "upgrade_membertier":
                return "upgrade_membertier", "ConfirmUpgrade"  # Send upgrade confirmation message

        # Offer secured credex path
        case ("offer_secured", "AmountInput"):
            return "offer_secured", "HandleInput"  # Get recipient handle from member and account details from credex-core
        case ("offer_secured", "HandleInput"):
            return "offer_secured", "ConfirmInput"  # Confirm amount, denom, issuer and recipient accounts
        case ("offer_secured", "ConfirmInput"):
            return "offer_secured", "Greeting"  # Send random greeting while api call processes
        case ("offer_secured", "Greeting"):
            return "offer_secured", "CreateCredexApiCall"  # Create offer
        case ("offer_secured", "CreateCredexApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)

        # Accept offer path
        case ("accept_offer", "OfferListDisplay"):
            return "accept_offer", "Greeting"  # Send random greeting while api call processes
        case ("accept_offer", "Greeting"):
            return "accept_offer", "AcceptOfferApiCall"  # Process selected offer acceptance
        case ("accept_offer", "AcceptOfferApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)

        # Decline offer path
        case ("decline_offer", "OfferListDisplay"):
            return "decline_offer", "ConfirmDeclineOffer"  # Show offer details and request confirmation
        case ("decline_offer", "ConfirmDeclineOffer"):
            return "decline_offer", "Greeting"  # Send random greeting while api call processes
        case ("decline_offer", "Greeting"):
            return "decline_offer", "DeclineOfferApiCall"  # Process selected offer decline
        case ("decline_offer", "DeclineOfferApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)

        # Cancel offer path
        case ("cancel_offer", "OfferListDisplay"):
            return "cancel_offer", "ConfirmCancelOffer"  # Show offer details and request confirmation
        case ("cancel_offer", "ConfirmCancelOffer"):
            return "cancel_offer", "Greeting"  # Send random greeting while api call processes
        case ("cancel_offer", "Greeting"):
            return "cancel_offer", "CancelOfferApiCall"  # Process selected offer cancel
        case ("cancel_offer", "CancelOfferApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)

        # View ledger path
        case ("view_ledger", "Greeting"):
            return "view_ledger", "LedgerManagement"  # Manages fetching and displaying ledger and selecting a credex
        case ("view_ledger", "LedgerManagement"):
            if component_result == "view_credex":
                return "view_credex", "Greeting"  # Send random greeting while api call processes
            if component_result == "send_account_dashboard":
                return "account", "AccountDashboard"  # Return to account dashboard

        # View credex path
        case ("view_credex", "Greeting"):
            return "view_credex", "GetAndDisplayCredex"  # Fetches and displays a credex
        case ("view_credex", "GetAndDisplayCredex"):
            if component_result == "account_dashboard":
                return "account", "AccountDashboard"  # Return to account dashboard
            if component_result == "view_counterparty":  # Placeholder for future implementation
                return "account", "AccountDashboard"  # Return to account dashboard for now since this won't actually happen

        # Ugrade member tier path
        case ("upgrade_membertier", "ConfirmUpgrade"):
            return "upgrade_membertier", "Greeting"  # Send random greeting while api call processes
        case ("upgrade_membertier", "Greeting"):
            return "upgrade_membertier", "UpgradeMembertierApiCall"  # Process tier upgrade
        case ("upgrade_membertier", "UpgradeMembertierApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)


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

    # Only proceed if activation was successful
    if not result.valid:
        logger.error(f"Component activation failed: {result.error}")
        return None

    # Determine next step in path
    logger.info("Getting next component...")
    next_step = get_next_component(path, component, state_manager)
    logger.info(f"Next step: {next_step}")
    logger.info(f"Final awaiting_input: {state_manager.is_awaiting_input()}")

    return next_step
