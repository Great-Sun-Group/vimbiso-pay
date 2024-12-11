"""Progressive implementation of the credex offer flow"""
import logging
import re
from typing import Any, Dict, Optional, Tuple

from core.messaging.flow import Flow, Step, StepType
from core.messaging.templates import ButtonSelection, ProgressiveInput
from core.messaging.types import Message as WhatsAppMessage
from core.transactions import TransactionOffer, TransactionType
from services.state.service import StateStage

logger = logging.getLogger(__name__)


class CredexOfferFlow(Flow):
    """Progressive flow for creating credex offers"""

    FLOW_ID = "credex_offer"
    VALID_DENOMINATIONS = {"USD", "ZWG", "XAU", "CAD"}
    AMOUNT_PATTERN = re.compile(r'^(?:([A-Z]{3})\s+)?(\d+(?:\.\d+)?)$')
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')  # Basic handle format validation

    def __init__(self, id: str, steps: list):
        super().__init__(id, self._create_steps())
        self.transaction_service = None  # Should be injected
        self.credex_service = None  # Should be injected
        self.state_service = None  # Should be injected

    def _extract_member_id(self, profile_data: Dict[str, Any]) -> Optional[str]:
        """Extract member ID from profile data"""
        try:
            # Try to get from action details first
            action = profile_data.get("action", {})
            if action:
                # Try details.memberID
                member_id = action.get("details", {}).get("memberID")
                if member_id:
                    return member_id
                # Try action.actor as fallback
                return action.get("actor")

            # Try dashboard path as fallback
            dashboard = profile_data.get("dashboard", {})
            if dashboard:
                # Look in accounts for owned account
                accounts = dashboard.get("accounts", [])
                for account in accounts:
                    if account.get("success") and account.get("data", {}).get("isOwnedAccount"):
                        auth_for = account.get("data", {}).get("authFor", [])
                        if auth_for:
                            return auth_for[0].get("memberID")

            return None
        except Exception as e:
            logger.error(f"Error extracting member ID: {str(e)}")
            return None

    def _extract_sender_account_info(self, profile_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Extract sender account info from profile data"""
        try:
            # Look in dashboard accounts for personal account
            dashboard = profile_data.get("dashboard", {})
            accounts = dashboard.get("accounts", [])
            for account in accounts:
                if (account.get("success") and
                        account["data"].get("accountHandle") == self.state.get("phone")):
                    account_data = account["data"]
                    return account_data.get("accountID"), account_data.get("accountName")

            # If no personal account found, try first owned account
            for account in accounts:
                if account.get("success") and account["data"].get("isOwnedAccount"):
                    account_data = account["data"]
                    return account_data.get("accountID"), account_data.get("accountName")

            return None, None
        except Exception as e:
            logger.error(f"Error extracting sender account info: {str(e)}")
            return None, None

    def initialize_from_profile(self, profile_data: Dict[str, Any]) -> None:
        """Initialize flow state from profile data"""
        if not profile_data:
            return

        # Extract member ID
        member_id = self._extract_member_id(profile_data)
        if member_id:
            # Update state with member ID
            current_state = self.state
            current_state["authorizer_member_id"] = member_id
            current_state["issuer_member_id"] = member_id
            self.state = current_state
            logger.debug(f"Initialized flow with member ID: {member_id}")

        # Extract sender account info
        sender_account_id, sender_account_name = self._extract_sender_account_info(profile_data)
        if sender_account_id:
            # Update state with sender account info
            current_state = self.state
            current_state["sender_account_id"] = sender_account_id
            current_state["sender_account"] = sender_account_name
            self.state = current_state
            logger.debug(f"Initialized flow with sender account: {sender_account_id}")

    def _validate_handle(self, handle: str) -> bool:
        """
        Validate handle format before transformation.
        Basic validation to ensure handle meets format requirements.
        """
        if not handle:
            logger.debug("Handle is empty")
            return False

        handle = handle.strip()
        if not handle:
            logger.debug("Handle is empty after stripping")
            return False

        if not self.HANDLE_PATTERN.match(handle):
            logger.debug(f"Handle doesn't match pattern: {self.HANDLE_PATTERN.pattern}")
            return False

        logger.debug("Handle validation successful")
        return True

    def _update_service_state(self, data: Dict[str, Any], update_from: str = None) -> None:
        """Update service state with fresh data"""
        try:
            if self.state_service and self.state.get("phone"):
                # Create new state with only essential data
                current_state = {
                    "profile": data,
                    "last_refresh": True,
                    "current_account": None,  # Force account reselection
                }

                # Use Flow's state management to get preserved fields
                clean_state = self._get_clean_state()
                current_state.update(clean_state)

                # Update state with proper context
                self.state_service.update_state(
                    user_id=self.state.get("phone"),
                    new_state=current_state,
                    stage=StateStage.MENU.value,
                    update_from=update_from or "credex_offer_update",
                    option="handle_action_menu"
                )
                logger.debug(f"Service state updated from {update_from}")
                logger.debug(f"Updated state: {current_state}")
        except Exception as e:
            logger.error(f"Error updating service state: {str(e)}")

    def _create_steps(self) -> list[Step]:
        """Create flow steps"""
        return [
            # Step 1: Amount Input
            Step(
                id="amount",
                type=StepType.TEXT_INPUT,
                stage=StateStage.CREDEX.value,
                message=lambda state: ProgressiveInput.create_prompt(
                    "Enter amount in USD or specify other denomination:",
                    [
                        "100",           # Default USD
                        "USD 100",       # Explicit USD
                        "ZWG 100",       # Zimbabwe Gold
                        "XAU 1"          # Gold
                    ],
                    state.get("phone", "")
                ),
                validation=self._validate_amount,
                transform=self._transform_amount
            ),

            # Step 2: Recipient Handle Input
            Step(
                id="handle",
                type=StepType.TEXT_INPUT,
                stage=StateStage.CREDEX.value,
                message=lambda state: ProgressiveInput.create_prompt(
                    "Enter recipient's account handle:",
                    [
                        "263123456789",
                        "vimbisopay_trust"
                    ],
                    state.get("phone", "")
                ),
                validation=self._validate_handle,
                transform=self._transform_handle,
                condition=lambda state: self._has_valid_amount(state)
            ),

            # Step 3: Final Confirmation
            Step(
                id="confirm",
                type=StepType.BUTTON_SELECT,
                stage=StateStage.CREDEX.value,
                message=self._create_final_confirmation_message,
                condition=lambda state: self._can_show_confirmation(state),
                validation=lambda value: value == "confirm",
                transform=self._transform_confirm
            )
        ]

    def _format_amount(self, amount: float, denomination: str) -> str:
        """Format amount based on denomination"""
        if denomination in {"USD", "ZWG", "CAD"}:
            return f"${amount:.2f} {denomination}"  # Added denomination for clarity
        elif denomination == "XAU":
            return f"{amount:.4f} {denomination}"
        return f"{amount} {denomination}"

    def _has_valid_amount(self, state: Dict[str, Any]) -> bool:
        """Check if state has valid amount data"""
        amount_data = state.get("amount", {})
        if not isinstance(amount_data, dict):
            logger.debug("Invalid amount data format")
            return False

        # Check direct amount and denomination fields
        return (
            isinstance(amount_data.get("amount"), (int, float)) and
            isinstance(amount_data.get("denomination"), str) and
            amount_data.get("denomination") in self.VALID_DENOMINATIONS
        )

    def _validate_amount(self, amount_str: str) -> bool:
        """Validate amount string format"""
        logger.debug(f"Validating amount: '{amount_str}'")
        if not amount_str:
            logger.debug("Amount is empty")
            return False

        amount_str = amount_str.strip().upper()
        logger.debug(f"Normalized amount: '{amount_str}'")

        match = self.AMOUNT_PATTERN.match(amount_str)
        if not match:
            logger.debug(f"Amount doesn't match pattern: {self.AMOUNT_PATTERN.pattern}")
            return False

        denom = match.group(1)
        logger.debug(f"Extracted denomination: {denom}")

        if denom and denom not in self.VALID_DENOMINATIONS:
            logger.debug(f"Invalid denomination: {denom}")
            return False

        logger.debug("Amount validation successful")
        return True

    def _transform_amount(self, amount_str: str) -> Dict[str, Any]:
        """Transform amount string to amount and denomination"""
        amount_str = amount_str.strip().upper()
        match = self.AMOUNT_PATTERN.match(amount_str)
        denom, amount = match.groups()

        # Return just the amount data for this step
        return {
            "amount": float(amount),
            "denomination": denom or "USD"
        }

    def _transform_handle(self, handle: str) -> Dict[str, Any]:
        """Transform handle with validation and account lookup"""
        if not self.credex_service:
            raise ValueError("Credex service not initialized")

        # Clean handle
        handle = handle.strip()

        # Validate handle with service
        success, handle_data = self.credex_service._member.validate_handle(handle)
        if not success:
            error_msg = handle_data.get("message", "Invalid recipient handle")
            raise ValueError(error_msg)

        # Extract account details
        receiver_data = handle_data.get("data", {})
        receiver_account_id = receiver_data.get("accountID")
        receiver_name = receiver_data.get("accountName")

        # Try action details path if needed
        if not receiver_account_id or not receiver_name:
            action_details = receiver_data.get("action", {}).get("details", {})
            receiver_account_id = receiver_account_id or action_details.get("accountID")
            receiver_name = receiver_name or action_details.get("accountName")

        if not receiver_account_id:
            raise ValueError("Could not find recipient's account")

        # Return just the handle data for this step
        return {
            "handle": handle,
            "receiver_account_id": receiver_account_id,
            "recipient_name": receiver_name or handle
        }

    def _transform_confirm(self, value: str) -> Dict[str, Any]:
        """Transform confirmation value"""
        # Return just the confirmation data for this step
        return {
            "confirmed": value == "confirm"
        }

    def _create_final_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Create final confirmation message"""
        # Get amount info
        amount_data = state.get("amount", {})
        if not isinstance(amount_data, dict):
            raise ValueError("Invalid amount data in state")

        amount = amount_data.get("amount")
        denomination = amount_data.get("denomination")
        if not amount or not denomination:
            raise ValueError("Missing amount or denomination")

        # Format amount based on denomination
        formatted_amount = self._format_amount(amount, denomination)

        # Get recipient info
        handle_data = state.get("handle", {})
        if not isinstance(handle_data, dict):
            raise ValueError("Invalid handle data in state")

        recipient_name = handle_data.get("recipient_name")
        if not recipient_name:
            raise ValueError("Missing recipient name")

        # Get sender account info from state
        sender_account = state.get("sender_account", "Your Account")

        # Format confirmation message with more detail
        message = (
            f"Please confirm the following transaction:\n\n"
            f"Amount: {formatted_amount}\n"
            f"From: {sender_account}\n"
            f"To: {recipient_name} ({handle_data['handle']})"
        )

        return ButtonSelection.create_buttons({
            "text": message,
            "buttons": [
                {"id": "confirm", "title": "Confirm"}
            ]
        }, state.get("phone", ""))

    def _has_required_data(self, state: Dict[str, Any]) -> bool:
        """Check if state has all required data"""
        logger.debug(f"Checking required data in state: {state}")

        # Check amount data
        amount_data = state.get("amount", {})
        if not isinstance(amount_data, dict):
            logger.debug("Invalid amount data format")
            return False
        if not amount_data.get("amount") or not amount_data.get("denomination"):
            logger.debug("Missing amount or denomination")
            return False

        # Check handle data
        handle_data = state.get("handle", {})
        if not isinstance(handle_data, dict):
            logger.debug("Invalid handle data format")
            return False
        if not handle_data.get("receiver_account_id") or not handle_data.get("recipient_name"):
            logger.debug("Missing receiver_account_id or recipient_name")
            return False

        # Check member IDs and account ID
        if not state.get("authorizer_member_id"):
            logger.debug("Missing authorizer_member_id")
            return False
        if not state.get("sender_account_id"):
            logger.debug("Missing sender_account_id")
            return False

        logger.debug("All required data present")
        return True

    def _can_show_confirmation(self, state: Dict[str, Any]) -> bool:
        """Check if we can show final confirmation"""
        # Check if we have all required data
        if not self._has_required_data(state):
            return False

        # Don't show confirmation if already confirmed
        if state.get("confirm", {}).get("confirmed") is True:
            return False

        return True

    def create_transaction(self) -> Optional[TransactionOffer]:
        """Create transaction offer from flow state"""
        # Check if we have all required data
        if not self._has_required_data(self.state):
            logger.error("Missing required data for transaction")
            logger.debug(f"Current state: {self.state}")
            return None

        # Check if confirmed
        if not self.state.get("confirm", {}).get("confirmed"):
            logger.error("Transaction not confirmed")
            return None

        # Get required data with validation
        amount_data = self.state.get("amount", {})
        handle_data = self.state.get("handle", {})

        # Create transaction offer
        return TransactionOffer(
            authorizer_member_id=self.state["authorizer_member_id"],
            issuer_member_id=self.state["authorizer_member_id"],  # Use authorizer_member_id for both
            receiver_account_id=handle_data["receiver_account_id"],
            amount=amount_data["amount"],
            denomination=amount_data["denomination"],
            type=TransactionType.SECURED_CREDEX,
            handle=handle_data["handle"],
            metadata={"full_name": handle_data["recipient_name"]}
        )

    def handle_offer_action(self, action: str, credex_id: str) -> Tuple[bool, str]:
        """Handle offer actions (accept/decline/cancel)"""
        if not self.credex_service:
            return False, "Credex service not initialized"

        try:
            if action == "accept":
                success, response = self.credex_service.accept_credex(credex_id)
            elif action == "decline":
                success, response = self.credex_service.decline_credex(credex_id)
            elif action == "cancel":
                success, response = self.credex_service.cancel_credex(credex_id)
            else:
                return False, f"Invalid action: {action}"

            if not success:
                return False, response.get("message") if isinstance(response, dict) else f"Failed to {action} offer"

            # Update service state with fresh data from response
            if isinstance(response, dict) and "data" in response:
                self._update_service_state(response["data"], f"credex_{action}_complete")

            return True, f"Offer {action}ed successfully"

        except Exception as e:
            logger.exception(f"Error handling offer {action}: {str(e)}")
            return False, str(e)

    @classmethod
    def get_flow_by_id(cls, flow_id: str) -> Optional[Flow]:
        """Get flow instance by ID"""
        if flow_id == cls.FLOW_ID:
            return cls(flow_id, [])
        return None

    def complete_flow(self) -> Tuple[bool, str]:
        """Complete the flow by creating and submitting the transaction"""
        try:
            # Create transaction offer
            offer = self.create_transaction()
            if not offer:
                return False, "Unable to create transaction offer - missing required data"

            # Submit to credex service
            if not self.credex_service:
                return False, "Credex service not initialized"

            # Convert TransactionOffer to dict with correct API field names
            offer_data = {
                "authorizer_member_id": offer.authorizer_member_id,
                "issuerAccountID": self.state["sender_account_id"],
                "receiverAccountID": offer.receiver_account_id,  # Correct API field name
                "InitialAmount": offer.amount,
                "Denomination": offer.denomination,
                "type": offer.type.value,
                "handle": offer.handle,
                "metadata": offer.metadata
            }

            success, response = self.credex_service.offer_credex(offer_data)
            if not success:
                return False, response.get("message", "Failed to create credex offer")

            # Update service state with fresh data from response
            if isinstance(response, dict) and "data" in response:
                self._update_service_state(response["data"], "credex_offer_complete")

            return True, "Credex offer created successfully"

        except Exception as e:
            logger.exception("Error completing flow")
            return False, str(e)
