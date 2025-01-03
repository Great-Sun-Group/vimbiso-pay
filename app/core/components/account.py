"""Account-related components"""
from typing import Any, Dict

from .base import Component
from core.utils.exceptions import ComponentException


class AccountSelect(Component):
    """Account selection component"""

    def validate(self, value: Any) -> Dict:
        """Validate account selection"""
        try:
            # Validate account ID format
            if not isinstance(value, str):
                raise ComponentException(
                    message="Account ID must be a string",
                    component="AccountSelect",
                    field="account_id",
                    value=value
                )

            # TODO: Validate against available accounts

            return {"valid": True}

        except ComponentException:
            raise

        except Exception as e:
            raise ComponentException(
                message=str(e),
                component="AccountSelect",
                field="account_id",
                value=value
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        return {
            "account_id": value
        }


class LedgerDisplay(Component):
    """Ledger display component"""

    def validate(self, value: Any) -> Dict:
        """Validate ledger data"""
        try:
            # Validate ledger data structure
            if not isinstance(value, dict):
                raise ComponentException(
                    message="Invalid ledger data format",
                    component="LedgerDisplay",
                    field="ledger_data",
                    value=value
                )

            # Validate required fields
            required = ["entries"]
            for field in required:
                if field not in value:
                    raise ComponentException(
                        message=f"Missing required field: {field}",
                        component="LedgerDisplay",
                        field="ledger_data",
                        value=value
                    )

            # Validate entries format
            entries = value["entries"]
            if not isinstance(entries, list):
                raise ComponentException(
                    message="Entries must be a list",
                    component="LedgerDisplay",
                    field="entries",
                    value=entries
                )

            # Validate entry format
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ComponentException(
                        message="Invalid entry format",
                        component="LedgerDisplay",
                        field="entry",
                        value=entry
                    )

                # Validate required entry fields
                required_entry = ["date", "description", "amount", "denom"]
                for field in required_entry:
                    if field not in entry:
                        raise ComponentException(
                            message=f"Missing required entry field: {field}",
                            component="LedgerDisplay",
                            field="entry",
                            value=entry
                        )

            return {"valid": True}

        except ComponentException:
            raise

        except Exception as e:
            raise ComponentException(
                message=str(e),
                component="LedgerDisplay",
                field="ledger_data",
                value=value
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified data"""
        return {
            "ledger_data": value
        }
