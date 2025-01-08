"""Component activation and branching logic.

This module handles activating components and branching based on their results.
Components handle their own validation and processing, this just handles "what's next".
Context is maintained to support reusable components.

Also handles default account setup for entry points (login/onboard).
"""

import logging
from typing import Any, Optional, Tuple

from core import components
from core.utils.exceptions import ComponentException

logger = logging.getLogger(__name__)


def _set_default_account(state_manager: Any) -> bool:
    """Set default account (currently PERSONAL) for new flows

    Returns:
        bool: True if account was set successfully
    """
    try:
        # Get dashboard directly from state
        dashboard = state_manager.get("dashboard")
        logger.info(f"Dashboard data: {dashboard}")
        if not dashboard:
            logger.error("No dashboard data when setting default account")
            return False

        accounts = dashboard.get("accounts", [])
        logger.info(f"Found accounts: {accounts}")
        if not accounts:
            logger.error("No accounts found when setting default account")
            return False

        personal_account = next(
            (acc for acc in accounts if acc.get("accountType") == "PERSONAL"),
            None
        )
        logger.info(f"Found personal account: {personal_account}")
        if not personal_account:
            logger.error("No PERSONAL account found when setting default account")
            return False

        state_manager.update_state({
            "active_account_id": personal_account["accountID"]
        })
        logger.info(f"Set active account ID: {personal_account['accountID']}")
        return True

    except Exception as e:
        logger.error(f"Error setting default account: {str(e)}")
        return False


def activate_component(component_type: str, state_manager: Any) -> Any:
    """Create and activate a component using state data

    Args:
        component_type: Type of component to activate
        state_manager: State manager instance for accessing data

    Returns:
        Component result
    """
    try:
        component_class = getattr(components, component_type)
        component = component_class()
        component.set_state_manager(state_manager)  # Use proper setter

        # Get flow data for component
        flow_data = state_manager.get_flow_data()

        # For display components, start fresh
        if hasattr(component, 'type') and isinstance(component.type, str):
            if component.type.endswith('_dashboard') or component.type == 'greeting':
                return component.validate({})

        return component.validate(flow_data)
    except ComponentException as e:
        # Ensure all required parameters are present
        if not all(k in e.details for k in ["component", "field", "value"]):
            raise ComponentException(
                message=str(e),
                component=component_type,
                field="validation",
                value=str(flow_data),
                validation=e.details.get("validation")
            )
        raise


def handle_component_result(context: str, component: str, result: Any, state_manager: Optional[Any] = None) -> Tuple[str, str]:
    """Handle component result and determine next component

    Args:
        context: Current context (e.g. "login", "onboard", "account")
        component: Currently active component
        result: Result from component

    Returns:
        Tuple[str, str]: Next (context, component) to activate
    """
    # Handle errors with validation state
    if isinstance(result, Exception):
        if isinstance(result, ComponentException):
            # Component validation failed with tracking
            validation = result.details.get("validation", {})
            if validation.get("attempts", 0) >= 3:
                # After 3 attempts, return to dashboard
                return "account", "AccountDashboard"
        # For other errors or validation attempts < 3, retry
        return context, component

    # Handle ValidationResult objects
    if hasattr(result, "valid"):
        if not result.valid:
            return context, component  # Retry on validation failure

        # Get value and metadata for flow control
        value = result.value or {}
        metadata = getattr(result, 'metadata', {}) or {}

        # Components can explicitly request to wait for input
        # This is needed for display/confirm components that need user interaction
        if metadata.get("await_input"):
            return context, component

        # Default behavior is to advance with the flow
        result = {
            **(value if isinstance(value, dict) else {"value": value}),
            "exit_condition": metadata.get("exit_condition"),
            "_metadata": {
                "value_type": type(value).__name__,
                "has_metadata": bool(metadata)
            }
        }

    # Branch based on context and component
    match (context, component):
        # Login context
        case ("login", "Greeting"):
            return "login", "LoginApiCall"

        case ("login", "LoginApiCall"):
            # Get metadata for flow control
            metadata = getattr(result, 'metadata', {}) or {}
            exit_condition = metadata.get("exit_condition")

            if exit_condition == "not_member":
                return "onboard", "Welcome"
            elif exit_condition == "success":
                # Set default account before proceeding
                if not state_manager:
                    return context, component  # Retry if no state manager
                if not _set_default_account(state_manager):
                    return context, component  # Retry if account setup fails
                return "account", "AccountDashboard"
            else:
                # No valid exit condition, stay on component
                return context, component

        # Onboard context
        case ("onboard", "Welcome"):
            return "onboard", "FirstNameInput"

        case ("onboard", "FirstNameInput"):
            return "onboard", "LastNameInput"

        case ("onboard", "LastNameInput"):
            return "onboard", "Greeting"

        case ("onboard", "Greeting"):
            return "onboard", "OnBoardMemberApiCall"

        case ("onboard", "OnBoardMemberApiCall"):
            if not state_manager:
                return context, component  # Retry if no state manager
            # Set default account before proceeding
            if not _set_default_account(state_manager):
                return context, component  # Retry if account setup fails
            return "account", "AccountDashboard"

        # Account context
        case ("account", "AccountDashboard"):
            match result.get("selection"):
                case "offer_secured":
                    return "offer_secured", "AmountInput"
                case "accept_offers":
                    return "accept_offers", "OfferListDisplay"
                case "decline_offers":
                    return "decline_offers", "OfferListDisplay"
                case "cancel_offers":
                    return "cancel_offers", "OfferListDisplay"
                case "view_ledger":
                    return "view_ledger", "ViewLedger"
                case "upgrade_membertier":
                    return "upgrade_membertier", "ConfirmUpgrade"

        # Offer context
        case ("offer_secured", "AmountInput"):
            return "offer_secured", "HandleInput"

        case ("offer_secured", "HandleInput"):
            return "offer_secured", "ConfirmInput"

        case ("offer_secured", "ConfirmInput"):
            return "offer_secured", "CreateCredexApiCall"

        case ("offer_secured", "Greeting"):
            return "offer_secured", "CreateCredexApiCall"

        case ("offer_secured", "CreateCredexApiCall"):
            if result.get("credex_created"):
                return "account", "AccountDashboard"
            else:
                return "account", "AccountDashboard"

        # Accept offer context
        case ("accept_offers", "OfferListDisplay"):
            return "accept_offers", "Greeting"

        case ("accept_offers", "Greeting"):
            return "accept_offers", "AcceptOfferApiCall"

        case ("accept_offers", "AcceptOfferApiCall"):
            return "account", "AccountDashboard"

        # Decline offer context
        case ("decline_offers", "OfferListDisplay"):
            return "decline_offers", "ConfirmAction"

        case ("decline_offers", "ConfirmAction"):
            return "decline_offers", "Greeting"

        case ("decline_offers", "Greeting"):
            return "decline_offers", "DeclineOfferApiCall"

        case ("decline_offers", "DeclineOfferApiCall"):
            return "account", "AccountDashboard"

        # Cancel offer context
        case ("cancel_offers", "OfferListDisplay"):
            return "cancel_offers", "ConfirmAction"

        case ("cancel_offers", "ConfirmAction"):
            return "cancel_offers", "Greeting"

        case ("cancel_offers", "Greeting"):
            return "cancel_offers", "CancelOfferApiCall"

        case ("cancel_offers", "CancelOfferApiCall"):
            return "account", "AccountDashboard"

        # Ledger context
        case ("view_ledger", "ViewLedger"):
            return "view_ledger", "Greeting"

        case ("view_ledger", "Greeting"):
            return "view_ledger", "GetLedgerApiCall"

        case ("view_ledger", "GetLedgerApiCall"):
            return "view_ledger", "DisplayLedgerSection"

        # Upgrade context
        case ("upgrade_membertier", "ConfirmUpgrade"):
            return "upgrade_membertier", "Greeting"

        case ("upgrade_membertier", "Greeting"):
            return "upgrade_membertier", "UpgradeMembertierApiCall"

        case ("upgrade_membertier", "UpgradeMembertierApiCall"):
            return "account", "AccountDashboard"


def process_component(context: str, component: str, state_manager: Any) -> Tuple[Any, str, str]:
    """Process a component and get next component with context

    Args:
        context: Current context
        component: Component to process
        state_manager: State manager instance for accessing data

    Returns:
        Tuple[Any, str, str]: (result, next_context, next_component)
    """
    result = activate_component(component, state_manager)
    next_context, next_component = handle_component_result(context, component, result, state_manager)
    return result, next_context, next_component
