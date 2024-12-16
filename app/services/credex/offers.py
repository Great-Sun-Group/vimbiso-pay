import logging
from typing import Any, Dict, List, Tuple

from core.transactions.exceptions import TransactionError

from .base import BaseCredExService
from .config import CredExEndpoints

logger = logging.getLogger(__name__)


class CredExOffersService(BaseCredExService):
    """Service for CredEx offer operations"""

    def offer_credex(self, offer_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer"""
        if not offer_data:
            return False, {"message": "Offer data is required"}

        try:
            # Remove any full_name field if present as it's not needed
            offer_data.pop("full_name", None)

            # Convert field names to match API expectations
            if "denomination" in offer_data:
                offer_data["Denomination"] = offer_data.pop("denomination")
            if "amount" in offer_data:
                offer_data["InitialAmount"] = offer_data.pop("amount")

            # Add required fields
            offer_data["credexType"] = "PURCHASE"
            offer_data["OFFERSorREQUESTS"] = "OFFERS"

            # Ensure securedCredex is present
            if "securedCredex" not in offer_data:
                offer_data["securedCredex"] = True

            response = self._make_request(
                CredExEndpoints.CREATE_CREDEX,
                payload=offer_data
            )

            data = self._validate_response(response)
            if data.get("data", {}).get("action", {}).get("type") == "CREDEX_CREATED":
                # Get the credexID from the response
                data["data"]["credexID"] = data["data"]["action"]["id"]
                logger.info("CredEx offer created successfully")
                return True, data
            else:
                # Extract error message from response
                error_msg = self._extract_error_message(response)
                logger.error(f"CredEx offer creation failed: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            # Error message is now a string
            error_msg = str(e)
            logger.warning(f"Transaction error creating offer: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"CredEx offer creation failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def confirm_credex(self, credex_id: str, issuer_account_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Confirm a CredEx offer"""
        if not credex_id:
            return False, {"message": "CredEx ID is required"}
        if not issuer_account_id:
            return False, {"message": "Account ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.ACCEPT_CREDEX,
                payload={
                    "credexID": credex_id,
                    "issuerAccountID": issuer_account_id
                }
            )

            data = self._validate_response(response)
            if data.get("data", {}).get("action", {}).get("type") == "CREDEX_ACCEPTED":
                logger.info("CredEx offer confirmed successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"CredEx offer confirmation failed: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error confirming offer: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"CredEx offer confirmation failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def accept_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer"""
        if not credex_id:
            return False, {"message": "CredEx ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.ACCEPT_CREDEX,
                payload={"credexID": credex_id}
            )

            data = self._validate_response(response)
            if data.get("data", {}).get("action", {}).get("type") == "CREDEX_ACCEPTED":
                logger.info("CredEx offer accepted successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"CredEx offer acceptance failed: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error accepting offer: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"CredEx offer acceptance failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def accept_bulk_credex(self, credex_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers"""
        if not credex_ids:
            return False, {"message": "CredEx IDs are required"}

        try:
            response = self._make_request(
                CredExEndpoints.ACCEPT_BULK_CREDEX,
                payload={"credexIDs": credex_ids}
            )

            data = self._validate_response(response)
            if data.get("summary", {}).get("accepted"):
                logger.info("Bulk CredEx offers accepted successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"Bulk CredEx offer acceptance failed: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error accepting bulk offers: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"Bulk CredEx offer acceptance failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def decline_credex(self, credex_id: str) -> Tuple[bool, str]:
        """Decline a CredEx offer"""
        if not credex_id:
            return False, "CredEx ID is required"

        try:
            response = self._make_request(
                CredExEndpoints.DECLINE_CREDEX,
                payload={"credexID": credex_id}
            )

            data = self._validate_response(response)
            if (data.get("message") == "Credex declined successfully" or
                    data.get("data", {}).get("action", {}).get("type") == "CREDEX_DECLINED"):
                logger.info("CredEx offer declined successfully")
                return True, "Decline successful"
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"CredEx offer decline failed: {error_msg}")
                return False, error_msg

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error declining offer: {error_msg}")
            return False, error_msg
        except Exception as e:
            logger.exception(f"CredEx offer decline failed: {str(e)}")
            return False, "An unexpected error occurred. Please try again."

    def cancel_credex(self, credex_id: str) -> Tuple[bool, str]:
        """Cancel a CredEx offer"""
        if not credex_id:
            return False, "CredEx ID is required"

        try:
            response = self._make_request(
                CredExEndpoints.CANCEL_CREDEX,
                payload={"credexID": credex_id}
            )

            data = self._validate_response(response)
            if data.get("message") == "Credex cancelled successfully":
                logger.info("CredEx offer cancelled successfully")
                return True, "Credex cancelled successfully"
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"CredEx offer cancellation failed: {error_msg}")
                return False, error_msg

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error cancelling offer: {error_msg}")
            return False, error_msg
        except Exception as e:
            logger.exception(f"CredEx offer cancellation failed: {str(e)}")
            return False, "An unexpected error occurred. Please try again."

    def get_credex(self, credex_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx offer"""
        if not credex_id:
            return False, {"message": "CredEx ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.GET_CREDEX,
                payload={"credexID": credex_id}
            )

            data = self._validate_response(response)
            if response.status_code == 200:
                logger.info("CredEx offer details fetched successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"CredEx offer details fetch failed: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error fetching offer: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"CredEx offer details fetch failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def get_ledger(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get member's ledger information"""
        if not member_id:
            return False, {"message": "Member ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.GET_LEDGER,
                payload={"memberId": member_id}
            )

            data = self._validate_response(response)
            if response.status_code == 200:
                logger.info("Ledger fetched successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"Ledger fetch failed: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error fetching ledger: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"Ledger fetch failed: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}
