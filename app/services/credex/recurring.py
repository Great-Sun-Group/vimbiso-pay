import logging
from datetime import datetime
from typing import Any, Dict, Set, Tuple

from .base import BaseCredExService
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class CredExRecurringService(BaseCredExService):
    """Service for recurring payment operations"""

    REQUIRED_PAYMENT_FIELDS: Set[str] = {
        "sourceAccountID",
        "templateType",
        "payFrequency",
        "startDate",
        "securedCredex",
        "amount",
        "denomination"
    }

    def _validate_payment_data(self, data: Dict[str, Any]) -> None:
        """Validate payment data"""
        if not data:
            raise ValidationError("Payment data is required")

        if missing := self.REQUIRED_PAYMENT_FIELDS - set(data.keys()):
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")

    def _process_payment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment data for API compatibility"""
        payment = data.copy()

        # Format date if needed
        if isinstance(payment.get("startDate"), datetime):
            payment["startDate"] = payment["startDate"].strftime("%Y-%m-%d")

        return payment

    def create_recurring(self, payment_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Create recurring payment"""
        try:
            self._validate_payment_data(payment_data)
            processed_data = self._process_payment_data(payment_data)

            response = self._make_request(
                'recurring', 'create',
                payload=processed_data
            )
            data = response.json()

            if data.get("data"):
                return True, data
            return False, {"message": "Failed to create recurring payment"}

        except ValidationError as e:
            return False, {"message": str(e)}
        except Exception as e:
            logger.error(f"Payment creation failed: {str(e)}")
            return False, {"message": str(e)}

    def accept_recurring(self, payment_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Accept recurring payment"""
        if not payment_id:
            raise ValidationError("Payment ID is required")

        try:
            response = self._make_request(
                'recurring', 'accept',
                payload={"paymentID": payment_id}
            )
            data = response.json()

            if data.get("data"):
                return True, data
            return False, {"message": "Failed to accept recurring payment"}

        except Exception as e:
            logger.error(f"Payment acceptance failed: {str(e)}")
            return False, {"message": str(e)}

    def cancel_recurring(self, payment_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Cancel recurring payment"""
        if not payment_id:
            raise ValidationError("Payment ID is required")

        try:
            response = self._make_request(
                'recurring', 'cancel',
                payload={"paymentID": payment_id}
            )
            data = response.json()

            if data.get("data"):
                return True, data
            return False, {"message": "Failed to cancel recurring payment"}

        except Exception as e:
            logger.error(f"Payment cancellation failed: {str(e)}")
            return False, {"message": str(e)}

    def get_recurring(self, payment_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get recurring payment details"""
        if not payment_id:
            raise ValidationError("Payment ID is required")

        try:
            response = self._make_request(
                'recurring', 'get',
                payload={"paymentID": payment_id}
            )
            data = response.json()

            if data.get("data"):
                return True, data
            return False, {"message": "Failed to get recurring payment details"}

        except Exception as e:
            logger.error(f"Payment details fetch failed: {str(e)}")
            return False, {"message": str(e)}
