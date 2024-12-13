import logging
from typing import Any, Dict, Tuple
from datetime import datetime

from core.transactions.exceptions import TransactionError
from .base import BaseCredExService
from .config import CredExEndpoints

logger = logging.getLogger(__name__)


class CredExRecurringService(BaseCredExService):
    """Service for recurring payment operations"""

    def create_recurring(self, payment_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create a recurring payment

        Args:
            payment_data: Dictionary containing:
                - sourceAccountID: ID of the source account
                - templateType: Type of recurring payment template
                - payFrequency: Payment frequency in days
                - startDate: Start date for recurring payment
                - memberTier: Target member tier (for subscriptions)
                - securedCredex: Whether credex is secured
                - amount: Payment amount
                - denomination: Payment denomination

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        if not payment_data:
            return False, {"message": "Payment data is required"}

        try:
            # Validate required fields
            required_fields = [
                "sourceAccountID", "templateType", "payFrequency", "startDate",
                "securedCredex", "amount", "denomination"
            ]
            for field in required_fields:
                if field not in payment_data:
                    return False, {"message": f"Missing required field: {field}"}

            # Ensure proper date format
            if isinstance(payment_data["startDate"], datetime):
                payment_data["startDate"] = payment_data["startDate"].strftime("%Y-%m-%d")

            response = self._make_request(
                CredExEndpoints.get_recurring_endpoint('CREATE'),
                payload=payment_data
            )

            data = self._validate_response(response, {
                400: "Invalid request",
                401: "Unauthorized access",
                404: "Account not found"
            })

            if response.status_code == 200:
                logger.info("Recurring payment created successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"Recurring payment creation failed: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error creating recurring payment: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"Failed to create recurring payment: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def accept_recurring(self, payment_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept a recurring payment

        Args:
            payment_id: ID of the recurring payment to accept

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        if not payment_id:
            return False, {"message": "Payment ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.get_recurring_endpoint('ACCEPT'),
                payload={"paymentID": payment_id}
            )

            data = self._validate_response(response)
            if response.status_code == 200:
                logger.info("Recurring payment accepted successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"Failed to accept recurring payment: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error accepting recurring payment: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"Failed to accept recurring payment: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def cancel_recurring(self, payment_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a recurring payment

        Args:
            payment_id: ID of the recurring payment to cancel

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        if not payment_id:
            return False, {"message": "Payment ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.get_recurring_endpoint('CANCEL'),
                payload={"paymentID": payment_id}
            )

            data = self._validate_response(response)
            if response.status_code == 200:
                logger.info("Recurring payment cancelled successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"Failed to cancel recurring payment: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error cancelling recurring payment: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"Failed to cancel recurring payment: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}

    def get_recurring(self, payment_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a recurring payment

        Args:
            payment_id: ID of the recurring payment to retrieve

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        if not payment_id:
            return False, {"message": "Payment ID is required"}

        try:
            response = self._make_request(
                CredExEndpoints.get_recurring_endpoint('GET'),
                payload={"paymentID": payment_id}
            )

            data = self._validate_response(response)
            if response.status_code == 200:
                logger.info("Recurring payment details fetched successfully")
                return True, data
            else:
                error_msg = self._extract_error_message(response)
                logger.error(f"Failed to get recurring payment details: {error_msg}")
                return False, {"message": error_msg}

        except TransactionError as e:
            error_msg = str(e)
            logger.warning(f"Transaction error fetching recurring payment: {error_msg}")
            return False, {"message": error_msg}
        except Exception as e:
            logger.exception(f"Failed to get recurring payment details: {str(e)}")
            return False, {"message": "An unexpected error occurred. Please try again."}
