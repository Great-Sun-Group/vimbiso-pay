"""Component system

This package provides the component system with:
- Base component interfaces
- Display components
- Input components
- API components
"""

# Base interfaces
from .base import Component, InputComponent, DisplayComponent, ApiComponent
from .confirm_base import ConfirmBase

# Display components
from .display_ledger_section import DisplayLedgerSection
from .greeting import Greeting
from .offer_list_display import OfferListDisplay
from .view_ledger import ViewLedger
from .welcome import Welcome

# Input components
from .amount_input import AmountInput
from .confirm_cancel_offer import ConfirmCancelOffer
from .confirm_decline_offer import ConfirmDeclineOffer
from .confirm_offer_secured import ConfirmOfferSecured
from .confirm_upgrade import ConfirmUpgrade
from .first_name_input import FirstNameInput
from .handle_input import HandleInput
from .last_name_input import LastNameInput

# API components
from .accept_offer_api_call import AcceptOfferApiCall
from .cancel_offer_api_call import CancelOfferApiCall
from .create_credex_api_call import CreateCredexApiCall
from .decline_offer_api_call import DeclineOfferApiCall
from .get_ledger_api_call import GetLedgerApiCall
from .login_api_call import LoginApiCall
from .onboard_member_api_call import OnBoardMemberApiCall
from .upgrade_membertier_api_call import UpgradeMembertierApiCall

__all__ = [
    # Base interfaces
    "Component",
    "ApiComponent",
    "DisplayComponent",
    "InputComponent",

    # Base interface extensions
    "ConfirmBase",

    # Display components
    "DisplayLedgerSection",
    "Greeting",
    "OfferListDisplay",
    "ViewLedger",
    "Welcome",

    # Input components
    "AmountInput",
    "FirstNameInput",
    "HandleInput",
    "LastNameInput",

    # API components
    "AcceptOfferApiCall",
    "CancelOfferApiCall",
    "CreateCredexApiCall",
    "DeclineOfferApiCall",
    "GetLedgerApiCall",
    "LoginApiCall",
    "OnBoardMemberApiCall",
    "UpgradeMembertierApiCall",

    # Confirm components
    "ConfirmCancelOffer",
    "ConfirmDeclineOffer",
    "ConfirmOfferSecured",
    "ConfirmUpgrade"
]
