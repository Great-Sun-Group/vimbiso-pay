"""State management for WhatsApp service"""
import logging
from typing import Any, Dict, Optional

from core.utils.state_validator import StateValidator
from core.utils.flow_audit import FlowAuditLogger
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateManager:
    """Helper class for managing state transitions"""

    @staticmethod
    def prepare_state_update(
        current_state: Dict[str, Any],
        flow_data: Optional[Dict[str, Any]] = None,
        clear_flow: bool = False,
        mobile_number: Optional[str] = None,
        preserve_validation: bool = True
    ) -> Dict[str, Any]:
        """Prepare state update with proper context preservation"""
        # For greeting messages (clear_flow=True), preserve critical fields
        if clear_flow:
            new_state = {
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account", {}),
                "jwt_token": current_state.get("jwt_token", ""),
                "member_id": current_state.get("member_id", ""),
                "account_id": current_state.get("account_id", ""),
                "_validation_context": {},
                "_validation_state": {},
                "_last_updated": audit.get_current_timestamp()
            }
            if mobile_number:
                new_state["mobile_number"] = mobile_number
            # Preserve authentication state
            if "authenticated" in current_state:
                new_state["authenticated"] = current_state["authenticated"]
            return new_state

        # Extract validation context if needed
        validation_context = {}
        if preserve_validation:
            validation_context = {
                k: v for k, v in current_state.items()
                if k.startswith('_') and k != '_previous_state'
            }

        # Build new state
        new_state = {
            "flow_data": flow_data,
            "profile": current_state.get("profile", {}),
            "current_account": current_state.get("current_account"),
            "jwt_token": current_state.get("jwt_token"),
            "member_id": current_state.get("member_id"),
            "account_id": current_state.get("account_id"),
            "_last_updated": audit.get_current_timestamp()
        }

        # Add mobile number if provided
        if mobile_number:
            new_state["mobile_number"] = mobile_number

        # Add validation context if preserving
        if preserve_validation:
            new_state.update(validation_context)

        # Preserve authentication state
        if "authenticated" in current_state:
            new_state["authenticated"] = current_state["authenticated"]

        return new_state

    @staticmethod
    def validate_and_update(
        state_manager: Any,
        new_state: Dict[str, Any],
        current_state: Dict[str, Any],
        operation: str,
        mobile_number: str
    ) -> Optional[WhatsAppMessage]:
        """Validate and update state with proper error handling"""
        try:
            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    mobile_number,
                    f"Failed to update state: {validation.error_message}"
                )

            # Log state transition
            audit.log_state_transition(
                "bot_service",
                current_state,
                new_state,
                "success"
            )

            # Update state
            state_manager.update_state(new_state, operation)
            return None

        except Exception as e:
            logger.error(f"State update error: {str(e)}")
            return WhatsAppMessage.create_text(
                mobile_number,
                f"❌ Failed to update state: {str(e)}"
            )
