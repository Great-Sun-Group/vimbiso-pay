"""State management for WhatsApp service"""
import logging
from typing import Any, Dict, Optional

# Core imports
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

# Local imports
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateManager:
    """Helper class for managing state transitions"""

    # Default flow data structure
    DEFAULT_FLOW_DATA = {
        "id": "user_state",
        "step": 0,
        "data": {
            "mobile_number": None,
            "flow_type": "auth",
            "_validation_context": {},
            "_validation_state": {}
        },
        "_previous_data": {}
    }

    @staticmethod
    def prepare_state_update(
        current_state: Dict[str, Any],
        flow_data: Optional[Dict[str, Any]] = None,
        clear_flow: bool = False,
        mobile_number: Optional[str] = None,
        preserve_validation: bool = True
    ) -> Dict[str, Any]:
        """Prepare state update with proper context preservation"""
        try:
            # Initialize or validate flow data structure
            if flow_data is None:
                flow_data = StateManager.DEFAULT_FLOW_DATA.copy()
                if mobile_number:
                    flow_data["data"]["mobile_number"] = mobile_number
            else:
                # Ensure flow data has required structure
                if "id" not in flow_data:
                    flow_data["id"] = "user_state"
                if "step" not in flow_data:
                    flow_data["step"] = 0
                if "data" not in flow_data:
                    flow_data["data"] = {}
                if "_previous_data" not in flow_data:
                    flow_data["_previous_data"] = {}

                # Ensure data has required fields
                if mobile_number:
                    flow_data["data"]["mobile_number"] = mobile_number

            # Extract validation context from current state if preserving
            validation_context = (
                {k: v for k, v in current_state.items()
                 if k.startswith('_') and k != '_previous_state'}
                if preserve_validation else {}
            )

            # Build new state with core fields
            new_state = {
                "flow_data": flow_data,  # Use complete flow data structure
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
                if isinstance(flow_data.get("data"), dict):
                    flow_data["data"]["mobile_number"] = mobile_number

            # Store validation context only in flow_data.data
            if preserve_validation and isinstance(flow_data.get("data"), dict):
                flow_data["data"].update({
                    "_validation_context": validation_context.get("_validation_context", {}),
                    "_validation_state": validation_context.get("_validation_state", {})
                })

            # Preserve authentication state
            if "authenticated" in current_state:
                new_state["authenticated"] = current_state["authenticated"]

            # Log state preparation
            logger.debug("Preparing state update:")
            logger.debug(f"Current state keys: {list(current_state.keys())}")
            logger.debug(f"New state keys: {list(new_state.keys())}")
            logger.debug(f"Flow data keys: {list(flow_data.keys())}")
            if isinstance(flow_data.get("data"), dict):
                logger.debug(f"Flow data.data keys: {list(flow_data['data'].keys())}")

            return new_state

        except Exception as e:
            logger.error(f"Error preparing state update: {str(e)}")
            raise ValueError(f"Failed to prepare state update: {str(e)}")

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
            # Start atomic update
            audit.log_flow_event(
                "bot_service",
                "state_update_start",
                operation,
                new_state,
                "in_progress"
            )

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    operation,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    mobile_number,
                    f"Failed to update state: {validation.error_message}"
                )

            try:
                # Attempt state update
                state_manager.update_state(new_state, operation)

                # Log successful transition only after update
                audit.log_state_transition(
                    "bot_service",
                    current_state,
                    new_state,
                    "success"
                )

                audit.log_flow_event(
                    "bot_service",
                    "state_update_complete",
                    operation,
                    new_state,
                    "success"
                )

                return None

            except Exception as update_error:
                # Rollback not needed as update_state should be atomic
                audit.log_flow_event(
                    "bot_service",
                    "state_update_error",
                    operation,
                    new_state,
                    "failure",
                    str(update_error)
                )
                raise

        except Exception as e:
            logger.error(f"State update error: {str(e)}")
            return WhatsAppMessage.create_text(
                mobile_number,
                f"❌ Failed to update state: {str(e)}"
            )
