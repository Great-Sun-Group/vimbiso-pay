"""Component system

This package provides the component system with:
- Base component interfaces
- Display components
- Input components
- API components
- Confirm components
"""

# Base interfaces
from .base import Component, InputComponent, DisplayComponent, ApiComponent
from .confirm import ConfirmBase

# Display components
from .display.greeting import Greeting

# Input components
from .input.welcome import Welcome
from .input.account_dashboard import AccountDashboard
from .input.display_ledger_section import DisplayLedgerSection
from .input.offer_list_display import OfferListDisplay
from .input.view_ledger import ViewLedger
from .input.amount_input import AmountInput
from .input.first_name_input import FirstNameInput
from .input.handle_input import HandleInput
from .input.last_name_input import LastNameInput

# API components
from .api.accept_offer_api_call import AcceptOfferApiCall
from .api.cancel_offer_api_call import CancelOfferApiCall
from .api.create_credex_api_call import CreateCredexApiCall
from .api.decline_offer_api_call import DeclineOfferApiCall
from .api.get_ledger_api_call import GetLedgerApiCall
from .api.login_api_call import LoginApiCall
from .api.onboard_member_api_call import OnBoardMemberApiCall
from .api.upgrade_membertier_api_call import UpgradeMembertierApiCall
from .api.validate_account_api_call import ValidateAccountApiCall

# Confirm components
from .confirm.confirm_cancel_offer import ConfirmCancelOffer
from .confirm.confirm_decline_offer import ConfirmDeclineOffer
from .confirm.confirm_offer_secured import ConfirmOfferSecured
from .confirm.confirm_upgrade import ConfirmUpgrade

__all__ = [
    # Base interfaces
    "Component",
    "ApiComponent",
    "DisplayComponent",
    "InputComponent",
    "ConfirmBase",

    # Display components
    "Greeting",

    # Input components
    "AccountDashboard",
    "DisplayLedgerSection",
    "OfferListDisplay",
    "ViewLedger",
    "Welcome",
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
    "ValidateAccountApiCall",

    # Confirm components
    "ConfirmCancelOffer",
    "ConfirmDeclineOffer",
    "ConfirmOfferSecured",
    "ConfirmUpgrade"
]
