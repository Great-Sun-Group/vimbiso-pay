"""Component activation and branching logic.

This module handles activating components and branching based on their results.
Components handle their own validation and processing, this just handles "what's next".
Context is maintained to support reusable components.
"""

from typing import Any, Tuple

from core import components


def activate_component(component_type: str, state_manager: Any) -> Any:
    """Create and activate a component using state data

    Args:
        component_type: Type of component to activate
        state_manager: State manager instance for accessing data

    Returns:
        Component result
    """
    component_class = getattr(components, component_type)
    component = component_class()
    component.state_manager = state_manager

    # Get input data from state
    message_data = state_manager.get("message", {})

    return component.validate(message_data)


def handle_component_result(context: str, component: str, result: Any) -> Tuple[str, str]:
    """Handle component result and determine next component

    Args:
        context: Current context (e.g. "login", "onboard", "account")
        component: Currently active component
        result: Result from component

    Returns:
        Tuple[str, str]: Next (context, component) to activate
    """
    # Handle errors uniformly
    if isinstance(result, Exception):
        return context, component  # Retry same component in same context

    # Branch based on context and component
    match (context, component):
        # Login context
        case ("login", "Greeting"):
            return "login", "LoginApiCall"

        case ("login", "LoginApiCall"):
            if result.get("not_found"):
                return "onboard", "Welcome"
            return "account", "AccountDashboard"

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
    next_context, next_component = handle_component_result(context, component, result)
    return result, next_context, next_component
