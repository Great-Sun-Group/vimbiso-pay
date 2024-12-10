import logging
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (InvalidAccountError, InvalidTransactionCommandError,
                         InvalidTransactionTypeError,
                         TransactionProcessingError,
                         TransactionValidationError)
from .interface import TransactionServiceInterface
from .types import (Account, Transaction, TransactionOffer, TransactionResult,
                    TransactionStatus, TransactionType)

logger = logging.getLogger(__name__)


class BaseTransactionService(TransactionServiceInterface):
    """Base class implementing common transaction functionality"""

    def create_offer(self, offer: TransactionOffer) -> TransactionResult:
        """Create a new transaction offer"""
        is_valid, errors = self.validate_offer(offer)
        if not is_valid:
            logger.warning(f"Offer validation failed: {errors}")
            return TransactionResult(
                success=False,
                error_message="Invalid transaction offer",
                details={"validation_errors": errors}
            )

        try:
            return self._process_offer(offer)
        except TransactionProcessingError as e:
            logger.error(f"Failed to process offer: {str(e)}")
            return TransactionResult(
                success=False,
                error_message=str(e)
            )

    def confirm_offer(self, transaction_id: str, issuer_account_id: str) -> TransactionResult:
        """Confirm a transaction offer"""
        try:
            self._validate_account_id(issuer_account_id)
            return self._confirm_transaction(transaction_id, issuer_account_id)
        except (InvalidAccountError, TransactionProcessingError) as e:
            logger.error(f"Failed to confirm offer: {str(e)}")
            return TransactionResult(
                success=False,
                error_message=str(e)
            )

    def process_command(
        self, command: str, member_id: str, account_id: str, denomination: str
    ) -> TransactionResult:
        """Process a transaction command"""
        try:
            parsed_command = self._parse_command(command)
            offer = self._create_offer_from_command(
                parsed_command, member_id, account_id, denomination
            )
            return self.create_offer(offer)
        except InvalidTransactionCommandError as e:
            logger.error(f"Invalid command format: {str(e)}")
            return TransactionResult(
                success=False,
                error_message=str(e)
            )

    def validate_offer(self, offer: TransactionOffer) -> Tuple[bool, Optional[Dict[str, List[str]]]]:
        """Validate a transaction offer"""
        errors = {}

        try:
            self._validate_member_ids(offer.authorizer_member_id, offer.issuer_member_id)
            self._validate_amount(offer.amount, offer.denomination)
            self._validate_transaction_type(offer.type)

            if offer.type == TransactionType.UNSECURED_CREDEX and not offer.due_date:
                errors["due_date"] = ["Due date is required for unsecured transactions"]

            return len(errors) == 0, errors if errors else None
        except (InvalidAccountError, InvalidTransactionTypeError) as e:
            return False, {"error": [str(e)]}

    def get_available_accounts(self, member_id: str) -> List[Account]:
        """Get list of available accounts for a member"""
        try:
            return self._fetch_member_accounts(member_id)
        except InvalidAccountError as e:
            logger.error(f"Failed to fetch accounts: {str(e)}")
            return []

    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get the status of a transaction"""
        try:
            return self._fetch_transaction_status(transaction_id)
        except TransactionProcessingError as e:
            logger.error(f"Failed to fetch transaction status: {str(e)}")
            return {
                "status": TransactionStatus.FAILED,
                "error": str(e)
            }

    def list_transactions(
        self,
        member_id: str,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Transaction]:
        """List transactions matching the given criteria"""
        try:
            return self._fetch_transactions(
                member_id, account_id, status, start_date, end_date
            )
        except TransactionProcessingError as e:
            logger.error(f"Failed to fetch transactions: {str(e)}")
            return []

    def _validate_member_ids(self, authorizer_id: str, issuer_id: str) -> None:
        """Validate member IDs"""
        if not authorizer_id or not issuer_id:
            raise InvalidAccountError("Both authorizer and issuer IDs are required")
        if authorizer_id == issuer_id:
            raise InvalidAccountError("Authorizer and issuer cannot be the same")

    def _validate_amount(self, amount: float, denomination: str) -> None:
        """Validate transaction amount"""
        if amount <= 0:
            raise TransactionValidationError("Amount must be greater than 0")
        if not denomination:
            raise TransactionValidationError("Denomination is required")

    def _validate_transaction_type(self, type_: TransactionType) -> None:
        """Validate transaction type"""
        if not isinstance(type_, TransactionType):
            raise InvalidTransactionTypeError(f"Invalid transaction type: {type_}")

    def _validate_account_id(self, account_id: str) -> None:
        """Validate account ID"""
        if not account_id:
            raise InvalidAccountError("Account ID is required")

    def _parse_command(self, command: str) -> Dict[str, Any]:
        """Parse a transaction command string

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Transaction provider must implement _parse_command method"
        )

    def _process_offer(self, offer: TransactionOffer) -> TransactionResult:
        """Process a transaction offer

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Transaction provider must implement _process_offer method"
        )

    def _confirm_transaction(
        self, transaction_id: str, issuer_account_id: str
    ) -> TransactionResult:
        """Confirm a transaction

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Transaction provider must implement _confirm_transaction method"
        )

    def _create_offer_from_command(
        self, command_data: Dict[str, Any], member_id: str, account_id: str, denomination: str
    ) -> TransactionOffer:
        """Create a transaction offer from command data

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Transaction provider must implement _create_offer_from_command method"
        )

    def _fetch_member_accounts(self, member_id: str) -> List[Account]:
        """Fetch accounts for a member

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Transaction provider must implement _fetch_member_accounts method"
        )

    def _fetch_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Fetch status of a transaction

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Transaction provider must implement _fetch_transaction_status method"
        )

    def _fetch_transactions(
        self,
        member_id: str,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Transaction]:
        """Fetch transactions matching criteria

        This should be implemented by specific provider implementations
        """
        raise NotImplementedError(
            "Transaction provider must implement _fetch_transactions method"
        )
