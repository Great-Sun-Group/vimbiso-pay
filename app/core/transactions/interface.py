from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from .types import Account, Transaction, TransactionOffer, TransactionResult


class TransactionServiceInterface(ABC):
    """Interface defining transaction service operations"""

    @abstractmethod
    def create_offer(self, offer: TransactionOffer) -> TransactionResult:
        """Create a new transaction offer

        Args:
            offer: The transaction offer details

        Returns:
            Result of the offer creation attempt
        """
        pass

    @abstractmethod
    def confirm_offer(self, transaction_id: str, issuer_account_id: str) -> TransactionResult:
        """Confirm a transaction offer

        Args:
            transaction_id: ID of the transaction to confirm
            issuer_account_id: ID of the issuing account

        Returns:
            Result of the confirmation attempt
        """
        pass

    @abstractmethod
    def process_command(self, command: str, member_id: str, account_id: str, denomination: str) -> TransactionResult:
        """Process a transaction command

        Args:
            command: The transaction command to process
            member_id: ID of the member initiating the command
            account_id: ID of the account to use
            denomination: Denomination denomination

        Returns:
            Result of the command processing
        """
        pass

    @abstractmethod
    def validate_offer(self, offer: TransactionOffer) -> Tuple[bool, Optional[Dict[str, List[str]]]]:
        """Validate a transaction offer

        Args:
            offer: The offer to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        pass

    @abstractmethod
    def get_available_accounts(self, member_id: str) -> List[Account]:
        """Get list of available accounts for a member

        Args:
            member_id: ID of the member

        Returns:
            List of available accounts
        """
        pass

    @abstractmethod
    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Get the status of a transaction

        Args:
            transaction_id: ID of the transaction

        Returns:
            Transaction status information
        """
        pass

    @abstractmethod
    def list_transactions(
        self,
        member_id: str,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Transaction]:
        """List transactions matching the given criteria

        Args:
            member_id: ID of the member
            account_id: Optional account ID to filter by
            status: Optional status to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            List of matching transactions
        """
        pass
