import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .base import BaseTransactionService
from .exceptions import (
    InvalidTransactionCommandError,
    TransactionProcessingError,
)
from .types import (
    Account,
    Transaction,
    TransactionOffer,
    TransactionResult,
    TransactionStatus,
    TransactionType,
)

logger = logging.getLogger(__name__)


class CredexTransactionService(BaseTransactionService):
    """CredEx-specific transaction service implementation"""

    def __init__(self, api_client):
        """Initialize with CredEx API client"""
        self.api_client = api_client

    def _parse_command(self, command: str) -> Dict[str, Any]:
        """Parse a CredEx transaction command string

        Supports formats:
        - amount => handle
        - amount -> handle
        """
        if not command or not isinstance(command, str):
            raise InvalidTransactionCommandError("Invalid command format")

        # Match amount => handle or amount -> handle
        pattern = r"^(\d+(?:\.\d+)?)\s*(?:=>|->)\s*(\w+)$"
        match = re.match(pattern, command.strip())

        if not match:
            raise InvalidTransactionCommandError(
                "Command must be in format: amount => handle or amount -> handle"
            )

        amount, handle = match.groups()
        try:
            return {
                "amount": float(amount),
                "handle": handle,
            }
        except ValueError:
            raise InvalidTransactionCommandError("Invalid amount format")

    def _create_offer_from_command(
        self, command_data: Dict[str, Any], member_id: str, account_id: str, denomination: str
    ) -> TransactionOffer:
        """Create a transaction offer from command data"""
        return TransactionOffer(
            authorizer_member_id=member_id,
            issuer_member_id=account_id,
            amount=command_data["amount"],
            currency=denomination,
            type=TransactionType.SECURED_CREDEX,
            handle=command_data["handle"],
            due_date=datetime.now() + timedelta(weeks=4),
        )

    def _process_offer(self, offer: TransactionOffer) -> TransactionResult:
        """Process a CredEx transaction offer"""
        try:
            payload = {
                "authorizer_member_id": offer.authorizer_member_id,
                "issuer_member_id": offer.issuer_member_id,
                "handle": offer.handle,
                "amount": offer.amount,
                "currency": offer.currency,
                "securedCredex": offer.type == TransactionType.SECURED_CREDEX,
            }

            if offer.due_date:
                payload["dueDate"] = int(offer.due_date.timestamp() * 1000)

            response = self.api_client.offer_credex(payload)

            if not response.get("success"):
                raise TransactionProcessingError(
                    response.get("error", "Failed to process offer")
                )

            return self._create_transaction_result(response["data"])
        except Exception as e:
            logger.error(f"Failed to process CredEx offer: {str(e)}")
            raise TransactionProcessingError(str(e))

    def _confirm_transaction(
        self, transaction_id: str, issuer_account_id: str
    ) -> TransactionResult:
        """Confirm a CredEx transaction"""
        try:
            response = self.api_client.confirm_credex(
                transaction_id, issuer_account_id
            )

            if not response.get("success"):
                raise TransactionProcessingError(
                    response.get("error", "Failed to confirm transaction")
                )

            return self._create_transaction_result(response["data"])
        except Exception as e:
            logger.error(f"Failed to confirm CredEx transaction: {str(e)}")
            raise TransactionProcessingError(str(e))

    def _fetch_member_accounts(self, member_id: str) -> List[Account]:
        """Fetch CredEx accounts for a member"""
        try:
            response = self.api_client.get_member_accounts(member_id)

            if not response.get("success"):
                raise TransactionProcessingError(
                    response.get("error", "Failed to fetch accounts")
                )

            accounts = []
            for account_data in response.get("data", {}).get("accounts", []):
                accounts.append(Account(
                    id=account_data["accountID"],
                    name=account_data["accountName"],
                    denomination=account_data["defaultDenom"],
                    metadata=account_data.get("metadata", {})
                ))
            return accounts
        except Exception as e:
            logger.error(f"Failed to fetch CredEx accounts: {str(e)}")
            raise TransactionProcessingError(str(e))

    def _fetch_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Fetch status of a CredEx transaction"""
        try:
            response = self.api_client.get_transaction_status(transaction_id)

            if not response.get("success"):
                raise TransactionProcessingError(
                    response.get("error", "Failed to fetch transaction status")
                )

            return response["data"]
        except Exception as e:
            logger.error(f"Failed to fetch CredEx transaction status: {str(e)}")
            raise TransactionProcessingError(str(e))

    def _fetch_transactions(
        self,
        member_id: str,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Transaction]:
        """Fetch CredEx transactions matching criteria"""
        try:
            filters = {
                "member_id": member_id,
                "account_id": account_id,
                "status": status,
                "start_date": start_date,
                "end_date": end_date
            }
            response = self.api_client.list_transactions(filters)

            if not response.get("success"):
                raise TransactionProcessingError(
                    response.get("error", "Failed to fetch transactions")
                )

            transactions = []
            for tx_data in response.get("data", {}).get("transactions", []):
                transactions.append(self._create_transaction_from_response(tx_data))
            return transactions
        except Exception as e:
            logger.error(f"Failed to fetch CredEx transactions: {str(e)}")
            raise TransactionProcessingError(str(e))

    def _create_transaction_result(self, response_data: Dict[str, Any]) -> TransactionResult:
        """Create a transaction result from API response"""
        action = response_data.get("action", {})
        if action.get("type") == "CREDEX_CREATED":
            details = action.get("details", {})
            return TransactionResult(
                success=True,
                transaction=self._create_transaction_from_response(details),
                details=details
            )
        return TransactionResult(
            success=False,
            error_message="Invalid response format"
        )

    def _create_transaction_from_response(self, tx_data: Dict[str, Any]) -> Transaction:
        """Create a transaction object from API response data"""
        return Transaction(
            id=tx_data["transactionID"],
            offer=TransactionOffer(
                authorizer_member_id=tx_data["authorizerMemberID"],
                issuer_member_id=tx_data["issuerMemberID"],
                amount=float(tx_data["amount"]),
                currency=tx_data["denomination"],
                type=TransactionType.SECURED_CREDEX if tx_data.get("securedCredex")
                else TransactionType.UNSECURED_CREDEX,
                handle=tx_data.get("handle"),
                due_date=datetime.fromtimestamp(int(tx_data["dueDate"]) / 1000)
                if tx_data.get("dueDate") else None,
                metadata=tx_data.get("metadata", {})
            ),
            status=TransactionStatus(tx_data["status"].lower()),
            created_at=datetime.fromtimestamp(int(tx_data["createdAt"]) / 1000),
            updated_at=datetime.fromtimestamp(int(tx_data["updatedAt"]) / 1000),
            completed_at=datetime.fromtimestamp(int(tx_data["completedAt"]) / 1000)
            if tx_data.get("completedAt") else None,
            error_message=tx_data.get("errorMessage"),
            metadata=tx_data.get("metadata", {})
        )
