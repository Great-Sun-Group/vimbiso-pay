"""Core state validation enforcing SINGLE SOURCE OF TRUTH"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set


@dataclass
class ValidationResult:
    """Result of state validation"""
    is_valid: bool
    error_message: Optional[str] = None


class StateValidator:
    """Validates core state structure focusing on SINGLE SOURCE OF TRUTH"""

    # Required fields that can't be modified
    CRITICAL_FIELDS = {"channel"}

    # Flow types that require authentication
    AUTHENTICATED_FLOWS = {
        "dashboard",    # Requires member dashboard access
        "offer",       # Requires member to make offers
        "accept",      # Requires member to accept offers
        "decline",     # Requires member to decline offers
        "cancel",      # Requires member to cancel offers
        "upgrade"      # Requires member to upgrade tier
    }

    # Valid step sequences for each flow type
    FLOW_STEPS = {
        "offer": ["amount", "handle", "confirm", "complete"],
        "accept": ["select", "confirm", "complete"],
        "decline": ["select", "confirm", "complete"],
        "cancel": ["select", "confirm", "complete"],
        "upgrade": ["confirm", "complete"]
    }

    # Required data fields for each step
    STEP_DATA_FIELDS = {
        "amount": {
            "amount": {
                "value": float,
                "denomination": str
            }
        },
        "handle": {
            "amount": {
                "value": float,
                "denomination": str
            },
            "handle": str
        },
        "confirm": {
            "amount": {
                "value": float,
                "denomination": str
            },
            "handle": str
            # confirmed field only required after button input
        },
        "complete": {
            "amount": {
                "value": float,
                "denomination": str
            },
            "handle": str,
            "confirmed": bool,
            "offer_id": str  # Required after successful creation
        },
        "select": {
            "credex_id": str,
            "action_type": str
        }
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate state structure enforcing SINGLE SOURCE OF TRUTH"""
        # Validate state is dictionary
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate channel exists and structure
        if "channel" not in state:
            return ValidationResult(
                is_valid=False,
                error_message="Missing required field: channel"
            )

        channel_validation = cls._validate_channel_data(state["channel"])
        if not channel_validation.is_valid:
            return channel_validation

        # Only validate optional fields if they exist
        if "flow_data" in state or "member_id" in state or "active_account_id" in state:
            # Check if this update requires authentication
            requires_auth = False
            if "flow_data" in state and state["flow_data"]:
                flow_type = state["flow_data"].get("flow_type")
                if flow_type in cls.AUTHENTICATED_FLOWS:
                    requires_auth = True

            # Validate authentication if required
            if requires_auth or state.get("member_id") is not None or state.get("active_account_id") is not None:
                # Skip auth validation if we're setting auth fields
                if not ("authenticated" in state and "jwt_token" in state):
                    if not state.get("authenticated"):
                        return ValidationResult(
                            is_valid=False,
                            error_message="Authentication required for this operation"
                        )
                    if not state.get("jwt_token"):
                        return ValidationResult(
                            is_valid=False,
                            error_message="Valid token required for this operation"
                        )

            # Validate flow_data structure if present and not empty
            if "flow_data" in state and state["flow_data"]:
                flow_validation = cls._validate_flow_data(state["flow_data"], state)
                if not flow_validation.is_valid:
                    return flow_validation

            # Validate accounts structure if present
            if "accounts" in state:
                accounts_validation = cls._validate_accounts(
                    state["accounts"],
                    state.get("active_account_id")
                )
                if not accounts_validation.is_valid:
                    return accounts_validation

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_channel_data(cls, channel: Any) -> ValidationResult:
        """Validate channel data structure"""
        if not isinstance(channel, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel data must be a dictionary"
            )

        # Required channel fields
        required_fields = {"type", "identifier"}
        missing_fields = required_fields - set(channel.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Channel data missing required fields: {', '.join(missing_fields)}"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_amount_data(cls, amount: Any) -> ValidationResult:
        """Validate amount data structure"""
        if not isinstance(amount, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Amount data must be a dictionary"
            )

        # Required amount fields
        required_fields = {"value", "denomination"}
        missing_fields = required_fields - set(amount.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Amount data missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(amount["value"], (int, float)):
            return ValidationResult(
                is_valid=False,
                error_message="Amount value must be numeric"
            )

        if not isinstance(amount["denomination"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Amount denomination must be string"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_handle_data(cls, handle: Any) -> ValidationResult:
        """Validate handle data structure"""
        if not isinstance(handle, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Handle data must be a dictionary"
            )

        # Required handle fields
        required_fields = {"account_name", "account_handle"}
        missing_fields = required_fields - set(handle.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Handle data missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(handle["account_name"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Account name must be string"
            )

        if not isinstance(handle["account_handle"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Account handle must be string"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_confirmation_data(cls, confirmation: Any) -> ValidationResult:
        """Validate confirmation data structure"""
        if not isinstance(confirmation, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Confirmation data must be a dictionary"
            )

        # Required confirmation fields
        required_fields = {"confirmed"}
        missing_fields = required_fields - set(confirmation.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Confirmation data missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(confirmation["confirmed"], bool):
            return ValidationResult(
                is_valid=False,
                error_message="Confirmed must be boolean"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_offer_id(cls, offer_id: Any) -> ValidationResult:
        """Validate offer ID"""
        if not isinstance(offer_id, str):
            return ValidationResult(
                is_valid=False,
                error_message="Offer ID must be string"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_auth_data(cls, auth: Any) -> ValidationResult:
        """Validate auth data structure"""
        if not isinstance(auth, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Auth data must be a dictionary"
            )

        # Required auth fields
        required_fields = {"token", "authenticated"}
        missing_fields = required_fields - set(auth.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Auth data missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(auth["authenticated"], bool):
            return ValidationResult(
                is_valid=False,
                error_message="Authenticated must be boolean"
            )

        if auth["token"] is not None and not isinstance(auth["token"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Token must be string or None"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_service_data(cls, service: Any) -> ValidationResult:
        """Validate service data structure"""
        if not isinstance(service, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Service data must be a dictionary"
            )

        # Required service fields
        required_fields = {"type", "config"}
        missing_fields = required_fields - set(service.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Service data missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(service["type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Service type must be string"
            )

        if not isinstance(service["config"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Service config must be dictionary"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_step_data(cls, step: Any) -> ValidationResult:
        """Validate step data structure"""
        if not isinstance(step, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Step data must be a dictionary"
            )

        # Required step fields
        required_fields = {"type", "data"}
        missing_fields = required_fields - set(step.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Step data missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(step["type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Step type must be string"
            )

        if not isinstance(step["data"], dict):
            return ValidationResult(
                is_valid=False,
                error_message="Step data must be dictionary"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_accounts(cls, accounts: Any, active_account_id: Optional[str] = None) -> ValidationResult:
        """Validate accounts structure and active account"""
        if not isinstance(accounts, list):
            return ValidationResult(
                is_valid=False,
                error_message="Accounts must be a list"
            )

        # Required account fields
        required_fields = {"accountID", "accountName", "accountHandle", "accountType"}

        # Validate each account
        for account in accounts:
            if not isinstance(account, dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Each account must be a dictionary"
                )

            # Check required fields
            missing_fields = required_fields - set(account.keys())
            if missing_fields:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Account missing required fields: {', '.join(missing_fields)}"
                )

            # Validate field types
            if not isinstance(account["accountID"], str):
                return ValidationResult(
                    is_valid=False,
                    error_message="Account ID must be string"
                )

            if not isinstance(account["accountName"], str):
                return ValidationResult(
                    is_valid=False,
                    error_message="Account name must be string"
                )

            if not isinstance(account["accountHandle"], str):
                return ValidationResult(
                    is_valid=False,
                    error_message="Account handle must be string"
                )

            if not isinstance(account["accountType"], str):
                return ValidationResult(
                    is_valid=False,
                    error_message="Account type must be string"
                )

        # Validate active_account_id references valid account if present
        if active_account_id is not None:
            account_ids = {account["accountID"] for account in accounts}
            if active_account_id not in account_ids:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Active account ID '{active_account_id}' not found in accounts"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_flow_data(cls, flow_data: Any, state: Dict[str, Any]) -> ValidationResult:
        """Validate flow data structure"""
        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Allow empty flow data for initial state
        if not flow_data:
            return ValidationResult(is_valid=True)

        # If flow data exists, validate required fields
        if "flow_type" in flow_data:
            # Flow type requires step tracking
            required_fields = {"step", "current_step", "flow_type"}
            missing_fields = required_fields - set(flow_data.keys())
            if missing_fields:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Flow data missing required fields: {', '.join(missing_fields)}"
                )

            # Validate step is integer
            if not isinstance(flow_data["step"], int):
                return ValidationResult(
                    is_valid=False,
                    error_message="Flow step must be integer"
                )

            # Validate current_step is string
            if not isinstance(flow_data["current_step"], str):
                return ValidationResult(
                    is_valid=False,
                    error_message="Flow current_step must be string"
                )

            # Validate flow_type is string and valid
            if not isinstance(flow_data["flow_type"], str):
                return ValidationResult(
                    is_valid=False,
                    error_message="Flow type must be string"
                )

            # Validate step sequence if flow type has defined steps
            if flow_data["flow_type"] in cls.FLOW_STEPS:
                valid_steps = cls.FLOW_STEPS[flow_data["flow_type"]]
                if flow_data["current_step"] not in valid_steps:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Invalid step '{flow_data['current_step']}' for flow type '{flow_data['flow_type']}'"
                    )

        # Validate step data if present
        if "data" in flow_data:
            step_validation = cls._validate_step_data(flow_data["data"])
            if not step_validation.is_valid:
                return step_validation

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_before_access(cls, state: Dict[str, Any], required_fields: Set[str]) -> ValidationResult:
        """Validate state before accessing specific fields"""
        # Validate state is dictionary
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate channel if required
        if "channel" in required_fields:
            if "channel" not in state:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required field: channel"
                )
            channel_validation = cls._validate_channel_data(state["channel"])
            if not channel_validation.is_valid:
                return channel_validation

        # Only validate auth for non-null member/account access
        if ("member_id" in required_fields and state.get("member_id") is not None or "active_account_id" in required_fields and state.get("active_account_id") is not None):
            # Skip auth validation if we're setting auth fields
            if not ("authenticated" in state and "jwt_token" in state):
                if not state.get("authenticated"):
                    return ValidationResult(
                        is_valid=False,
                        error_message="Authentication required for member operations"
                    )
                if not state.get("jwt_token"):
                    return ValidationResult(
                        is_valid=False,
                        error_message="Valid token required for member operations"
                    )

        # Validate accounts if required
        if "accounts" in required_fields:
            if "accounts" not in state:
                return ValidationResult(
                    is_valid=False,
                    error_message="Missing required field: accounts"
                )
            accounts_validation = cls._validate_accounts(
                state["accounts"],
                state.get("active_account_id")
            )
            if not accounts_validation.is_valid:
                return accounts_validation

        # Validate flow_data structure if being accessed and not empty
        if "flow_data" in required_fields and "flow_data" in state and state["flow_data"]:
            flow_validation = cls._validate_flow_data(state["flow_data"], state)
            if not flow_validation.is_valid:
                return flow_validation

        return ValidationResult(is_valid=True)
