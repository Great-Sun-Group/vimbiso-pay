import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseTransactionService
from .exceptions import (InvalidTransactionCommandError,
                         TransactionProcessingError)
from .types import (Account, Transaction, TransactionOffer, TransactionResult,
                    TransactionStatus, TransactionType)

logger = logging.getLogger(__name__)


class CredexTransactionService(BaseTransactionService):
    """CredEx-specific transaction service implementation"""

    def __init__(self, api_client):
        """Initialize with CredEx API client"""
        self.api_client = api_client

    def process_command(
        self, command: str, member_id: str, account_id: str, denomination: str
    ) -> TransactionResult:
        """Process a CredEx command string"""
        try:
            command_data = self._parse_command(command)
            offer = self._create_offer_from_command(
                command_data, member_id, account_id, denomination
            )
            return self._process_offer(offer)
        except InvalidTransactionCommandError as e:
            return TransactionResult(
                success=False,
                error_message=str(e)
            )

    def get_available_accounts(self, member_id: str) -> List[Account]:
        """Get available accounts for a member"""
        return self._fetch_member_accounts(member_id)

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
            denomination=denomination,
            type=TransactionType.SECURED_CREDEX,
            handle=command_data["handle"],
            due_date=datetime.now() + timedelta(weeks=4),
        )

    def _process_offer(self, offer: TransactionOffer) -> TransactionResult:
        """Process a CredEx transaction offer"""
        try:
            # First validate the handle if not already validated
            if not offer.receiver_account_id and offer.handle:
                success, handle_data = self.api_client._member.validate_handle(offer.handle)
                if not success:
                    return TransactionResult(
                        success=False,
                        error_message=handle_data.get("message", "Invalid recipient handle")
                    )
                offer.receiver_account_id = handle_data.get("data", {}).get("accountID")
                if not offer.receiver_account_id:
                    return TransactionResult(
                        success=False,
                        error_message="Could not find recipient's account"
                    )

            payload = {
                "authorizer_member_id": offer.authorizer_member_id,
                "issuerAccountID": offer.issuer_member_id,
                "receiverAccountID": offer.receiver_account_id,
                "amount": offer.amount,
                "denomination": offer.denomination,
                "securedCredex": offer.type == TransactionType.SECURED_CREDEX,
            }

            if offer.due_date:
                payload["dueDate"] = int(offer.due_date.timestamp() * 1000)

            response = self.api_client.offer_credex(payload)

            if not response[0]:  # Check first element of tuple for success
                error_data = response[1]
                # First try to get the detailed error message
                error_msg = error_data.get("message")
                if not error_msg:
                    # Check for error in action details
                    action = error_data.get("data", {}).get("action", {})
                    if action.get("type") == "CREDEX_CREATE_FAILED":
                        details = action.get("details", {})
                        if details.get("reason"):
                            error_msg = details["reason"]

                # If still no message, check other possible locations
                if not error_msg:
                    error_msg = (
                        error_data.get("error") or
                        error_data.get("detail") or
                        "Failed to process offer"
                    )

                return TransactionResult(
                    success=False,
                    error_message=error_msg
                )

            return self._create_transaction_result(response[1].get("data", {}))
        except TransactionProcessingError as e:
            logger.error(f"Failed to process CredEx offer: {str(e)}")
            return TransactionResult(
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error processing CredEx offer: {str(e)}")
            return TransactionResult(
                success=False,
                error_message=str(e)
            )

    def _fetch_member_accounts(self, member_id: str) -> List[Account]:
        """Fetch CredEx accounts for a member"""
        try:
            response = self.api_client.get_member_accounts(member_id)

            if not response[0]:  # Check first element of tuple for success
                error_data = response[1]
                error_msg = (
                    error_data.get("message") or
                    error_data.get("error") or
                    error_data.get("detail") or
                    "Failed to fetch accounts"
                )
                raise TransactionProcessingError(error_msg)

            accounts = []
            for account_data in response[1].get("data", {}).get("accounts", []):
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

    def _fetch_transaction_status(self, credex_id: str) -> Dict[str, Any]:
        """Fetch status of a CredEx transaction"""
        try:
            response = self.api_client.get_transaction_status(credex_id)

            if not response[0]:  # Check first element of tuple for success
                error_data = response[1]
                error_msg = (
                    error_data.get("message") or
                    error_data.get("error") or
                    error_data.get("detail") or
                    "Failed to fetch transaction status"
                )
                raise TransactionProcessingError(error_msg)

            return response[1].get("data", {})
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

            if not response[0]:  # Check first element of tuple for success
                error_data = response[1]
                error_msg = (
                    error_data.get("message") or
                    error_data.get("error") or
                    error_data.get("detail") or
                    "Failed to fetch transactions"
                )
                raise TransactionProcessingError(error_msg)

            transactions = []
            for tx_data in response[1].get("data", {}).get("transactions", []):
                transactions.append(self._create_transaction_from_response(tx_data))
            return transactions
        except Exception as e:
            logger.error(f"Failed to fetch CredEx transactions: {str(e)}")
            raise TransactionProcessingError(str(e))

    def _create_transaction_result(self, response_data: Dict[str, Any]) -> TransactionResult:
        """Create a transaction result from API response"""
        action = response_data.get("action", {})
        if action.get("type") == "CREDEX_CREATED":
            details = action.get("details", {}).copy()
            # Add fields from action
            details["credexID"] = action.get("id")
            details["authorizerMemberID"] = action.get("actor")
            details["issuerAccountID"] = details.get("issuerAccountID", "")  # Default empty string
            details["status"] = "pending"  # New offers are always pending
            details["createdAt"] = int(datetime.fromisoformat(action["timestamp"]).timestamp() * 1000)
            details["updatedAt"] = details["createdAt"]  # Same as created for new offers

            # Add metadata including receiver name
            metadata = {
                "full_name": details.get("receiverAccountName", "")
            }

            # Create transaction with metadata
            transaction = self._create_transaction_from_response({
                **details,
                "metadata": metadata
            })

            return TransactionResult(
                success=True,
                transaction=transaction,
                details=details
            )
        return TransactionResult(
            success=False,
            error_message="Invalid response format"
        )

    def _create_transaction_from_response(self, tx_data: Dict[str, Any]) -> Transaction:
        """Create a transaction object from API response data"""
        # Ensure metadata includes receiver name if available
        metadata = tx_data.get("metadata", {})
        if not metadata.get("full_name") and tx_data.get("receiverAccountName"):
            metadata["full_name"] = tx_data["receiverAccountName"]

        return Transaction(
            id=tx_data["credexID"],
            offer=TransactionOffer(
                authorizer_member_id=tx_data["authorizerMemberID"],
                issuer_member_id=tx_data["issuerAccountID"],
                receiver_account_id=tx_data.get("receiverAccountID"),
                amount=float(tx_data["amount"]),
                denomination=tx_data["denomination"],  # Use denomination consistently
                type=TransactionType.SECURED_CREDEX if tx_data.get("securedCredex")
                else TransactionType.UNSECURED_CREDEX,
                handle=tx_data.get("handle"),
                due_date=datetime.fromtimestamp(int(tx_data["dueDate"]) / 1000)
                if tx_data.get("dueDate") else None,
                metadata=metadata
            ),
            status=TransactionStatus(tx_data["status"].lower()),
            created_at=datetime.fromtimestamp(int(tx_data["createdAt"]) / 1000),
            updated_at=datetime.fromtimestamp(int(tx_data["updatedAt"]) / 1000),
            completed_at=datetime.fromtimestamp(int(tx_data["completedAt"]) / 1000)
            if tx_data.get("completedAt") else None,
            error_message=tx_data.get("errorMessage"),
            metadata=metadata
        )
