"""State machine for application flow paths.

This module defines a simple state machine that manages user flows through:
1. Authentication and registration paths
2. Main menu navigation
3. Feature-specific paths (offers, ledger, upgrades)

The state machine:
- Activates components at each step
- Determines next step through branching logic
- Returns to main menu after completing operations

Components are responsible for their own:
- Validation and processing
- State management
- Error handling

The branching logic (embedded in match statements) organizes paths into:
- Authentication paths (login, verification)
- Registration paths (user details, account creation)
- Main menu path (dashboard navigation)
- Offer paths (creation, acceptance, decline, cancellation)
- Account management paths (ledger, tier upgrades)
"""

import logging
from typing import Tuple

from core import components
from core.config.interface import StateManagerInterface

logger = logging.getLogger(__name__)


def activate_component(component_type: str, state_manager: StateManagerInterface) -> None:
    """Create and activate a component for the current path step.

    Handles component processing:
    1. Creates component instance
    2. Configures state management
    3. Activates component logic
    4. Validates component state

    Args:
        component_type: Component for this step (e.g. "Greeting", "LoginApiCall")
        state_manager: State manager for component configuration and validation

    Raises:
        ComponentException: If component creation, activation, or validation fails
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Creating component for step: {component_type}")

    # Create component for this step
    component_class = getattr(components, component_type)
    component = component_class()
    component.set_state_manager(state_manager)

    # Activate component (it will get data from state_manager)
    component.validate(None)


def get_next_component(
    context: str,
    component: str,
    state_manager: StateManagerInterface
) -> Tuple[str, str]:
    """Determine next step based on current path and state.

    Handles progression through:
    - Authentication and registration flows
    - Main menu navigation
    - Feature-specific operations
    - Return to main menu after completion

    Args:
        context: Path category (e.g. "login", "offer_secured", "account")
        component: Current step's component in the path
        state_manager: State manager for checking awaiting_input and path state

    Returns:
        Tuple[str, str]: Next step (context, component) in the current path
    """
    # Check if component is awaiting input
    flow_state = state_manager.get_flow_state()
    if flow_state.get("awaiting_input"):
        return context, component  # Stay at current step until input received

    # Branch based on current path
    match (context, component):
        # Authentication paths
        case ("login", "Greeting"):
            return "login", "LoginApiCall"  # Check if user exists in system
        case ("login", "LoginApiCall"):
            return "onboard", "Welcome"  # Component updates state for new/existing user

        # Registration paths
        case ("onboard", "Welcome"):
            return "onboard", "FirstNameInput"  # Start collecting user details
        case ("onboard", "FirstNameInput"):
            return "onboard", "LastNameInput"  # Continue with user details
        case ("onboard", "LastNameInput"):
            return "onboard", "Greeting"  # Show welcome after details collected
        case ("onboard", "Greeting"):
            return "onboard", "OnBoardMemberApiCall"  # Create account with collected details
        case ("onboard", "OnBoardMemberApiCall"):
            return "account", "AccountDashboard"  # Return to main menu after completing onboarding

        # Main menu path
        case ("account", "AccountDashboard"):
            return "account", "AccountDashboard"  # Component updates state based on user selection

        # Offer creation paths
        case ("offer_secured", "AmountInput"):
            return "offer_secured", "HandleInput"  # Start collecting offer details
        case ("offer_secured", "HandleInput"):
            return "offer_secured", "ConfirmInput"  # Get recipient handle
        case ("offer_secured", "ConfirmInput"):
            return "offer_secured", "CreateCredexApiCall"  # Verify offer details
        case ("offer_secured", "Greeting"):
            return "offer_secured", "CreateCredexApiCall"  # Create offer with verified details
        case ("offer_secured", "CreateCredexApiCall"):
            return "account", "AccountDashboard"  # Return to main menu after offer creation

        # Offer management paths
        case ("accept_offer", "OfferListDisplay"):
            return "accept_offer", "Greeting"  # Show available offers
        case ("accept_offer", "Greeting"):
            return "accept_offer", "AcceptOfferApiCall"  # Process selected offer
        case ("accept_offer", "AcceptOfferApiCall"):
            return "account", "AccountDashboard"  # Return to main menu after accepting offer

        case ("decline_offer", "OfferListDisplay"):
            return "decline_offer", "ConfirmAction"  # Show offers and request confirmation
        case ("decline_offer", "ConfirmAction"):
            return "decline_offer", "Greeting"  # Confirm decline action
        case ("decline_offer", "Greeting"):
            return "decline_offer", "DeclineOfferApiCall"  # Process decline after confirmation
        case ("decline_offer", "DeclineOfferApiCall"):
            return "account", "AccountDashboard"  # Return to main menu after declining offer

        case ("cancel_offer", "OfferListDisplay"):
            return "cancel_offer", "ConfirmAction"  # Show offers and request confirmation
        case ("cancel_offer", "ConfirmAction"):
            return "cancel_offer", "Greeting"  # Confirm cancel action
        case ("cancel_offer", "Greeting"):
            return "cancel_offer", "CancelOfferApiCall"  # Process cancel after confirmation
        case ("cancel_offer", "CancelOfferApiCall"):
            return "account", "AccountDashboard"  # Return to main menu after canceling offer

        # Account management paths
        case ("view_ledger", "ViewLedger"):
            return "view_ledger", "Greeting"  # Show ledger view options
        case ("view_ledger", "Greeting"):
            return "view_ledger", "GetLedgerApiCall"  # Fetch ledger data
        case ("view_ledger", "GetLedgerApiCall"):
            return "view_ledger", "DisplayLedgerSection"  # Show fetched ledger data

        case ("upgrade_membertier", "ConfirmUpgrade"):
            return "upgrade_membertier", "Greeting"  # Request upgrade confirmation
        case ("upgrade_membertier", "Greeting"):
            return "upgrade_membertier", "UpgradeMembertierApiCall"  # Process tier upgrade
        case ("upgrade_membertier", "UpgradeMembertierApiCall"):
            return "account", "AccountDashboard"  # Return to main menu after upgrading tier


def process_component(context: str, component: str, state_manager: StateManagerInterface) -> Tuple[str, str]:
    """Process current step and determine next step in application paths.

    Handles the complete step processing:
    1. Activates component for current step
    2. Lets component process its logic
    3. Determines next step in path
    4. Returns to main menu when complete

    Args:
        context: Path category (e.g. "login", "offer_secured", "account")
        component: Current step's component in the path
        state_manager: State manager for component activation and path control

    Returns:
        Tuple[str, str]: Next step (context, component) in the current path
    """
    # Activate component for current step (errors will bubble up)
    activate_component(component, state_manager)

    # Determine next step in path
    return get_next_component(context, component, state_manager)
