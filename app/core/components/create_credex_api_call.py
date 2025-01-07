"""Create Credex API call component

This component handles creating a new Credex offer through the API.
"""

from typing import Any, Dict

from core.utils.error_types import ValidationResult

from .base import Component


class CreateCredexApiCall(Component):
    """Handles creating a new Credex offer"""

    def __init__(self):
        super().__init__("create_credex_api")
        self.state_manager = None
        self.bot_service = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def set_bot_service(self, bot_service: Any) -> None:
        """Set bot service for API access"""
        self.bot_service = bot_service

    def validate(self, value: Any) -> ValidationResult:
        """Call createCredex endpoint and validate response"""
        # Validate state manager and bot service are set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "create_credex"}
            )

        if not self.bot_service:
            return ValidationResult.failure(
                message="Bot service not set",
                field="bot_service",
                details={"component": "create_credex"}
            )

        # Get offer data from state
        flow_data = self.state_manager.get_flow_state()
        if not flow_data or "data" not in flow_data:
            return ValidationResult.failure(
                message="No offer data found",
                field="flow_data",
                details={"component": "create_credex"}
            )

        # Get member ID from state
        member_id = self.state_manager.get_member_id()
        if not member_id:
            return ValidationResult.failure(
                message="No member ID found",
                field="member_id",
                details={"component": "create_credex"}
            )

        # Get active account ID from state
        active_account_id = self.state_manager.get("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"component": "create_credex"}
            )

        # Get offer details from flow data
        offer_data = flow_data["data"]
        amount = offer_data.get("amount")
        handle = offer_data.get("handle")

        if not amount or not handle:
            return ValidationResult.failure(
                message="Missing required offer fields",
                field="offer_data",
                details={
                    "missing_fields": [
                        "amount" if not amount else None,
                        "handle" if not handle else None
                    ]
                }
            )

        # Call createCredex endpoint
        from core.api.credex import create_credex
        success, message = create_credex(
            bot_service=self.bot_service,
            member_id=member_id,
            account_id=active_account_id,
            amount=amount,
            handle=handle
        )

        if not success:
            return ValidationResult.failure(
                message=f"Failed to create Credex: {message}",
                field="api_call",
                details={"error": message}
            )

        # Get API response from state
        flow_data = self.state_manager.get_flow_state()
        if not flow_data or "data" not in flow_data:
            return ValidationResult.failure(
                message="No state data after creating Credex",
                field="flow_data",
                details={"component": "create_credex"}
            )

        api_response = flow_data["data"].get("api_response")
        if not api_response:
            return ValidationResult.failure(
                message="No API response data found",
                field="api_response",
                details={"flow_data": flow_data["data"]}
            )

        return ValidationResult.success(api_response)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data"""
        return {
            "credex_id": value.get("credexID"),
            "amount": value.get("amount"),
            "handle": value.get("handle"),
            "credex_created": True
        }
