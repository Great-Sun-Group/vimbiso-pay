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

    # Class-level constants
    DEFAULT_FLOW_DATA = {
        "id": "user_state",
        "step": 0,
        "data": {
            "flow_type": "auth",
            "_validation_context": {},
            "_validation_state": {}
        },
        "_previous_data": {}
    }

    DEFAULT_CHANNEL_DATA = {
        "type": "whatsapp",  # Default to WhatsApp for backward compatibility
        "identifier": None,  # Channel-specific identifier (e.g. phone number)
        "metadata": {}
    }

    @staticmethod
    def get_member_id(state: Dict[str, Any]) -> Optional[str]:
        """Get member ID from state"""
        return state.get("member_id")

    @staticmethod
    def get_channel_identifier(state: Dict[str, Any]) -> Optional[str]:
        """Get channel identifier from state"""
        return state.get("channel", {}).get("identifier")

    @staticmethod
    def get_channel_type(state: Dict[str, Any]) -> str:
        """Get channel type from state"""
        return state.get("channel", {}).get("type", "whatsapp")

    @staticmethod
    def create_channel_data(identifier: Optional[str] = None, channel_type: str = "whatsapp") -> Dict[str, Any]:
        """Create channel data structure"""
        return {
            "type": channel_type,
            "identifier": identifier,
            "metadata": {}
        }

    @staticmethod
    def prepare_state_update(
        current_state: Dict[str, Any],
        flow_data: Optional[Dict[str, Any]] = None,
        clear_flow: bool = False,
        channel_identifier: Optional[str] = None,
        preserve_validation: bool = True
    ) -> Dict[str, Any]:
        """Prepare state update with proper context preservation"""
        try:
            # Initialize or validate flow data structure
            if flow_data is None:
                flow_data = StateManager.DEFAULT_FLOW_DATA.copy()
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

            # Extract validation context from current state if preserving
            validation_context = (
                {k: v for k, v in current_state.items()
                 if k.startswith('_') and k != '_previous_state'}
                if preserve_validation else {}
            )

            # Preserve parent service reference if exists
            parent_service = None
            if current_state.get("flow_data", {}).get("_parent_service"):
                parent_service = current_state["flow_data"]["_parent_service"]
            elif flow_data.get("_parent_service"):
                parent_service = flow_data["_parent_service"]

            # Preserve flow type from flow data
            flow_type = None
            if isinstance(flow_data, dict):
                flow_type = flow_data.get("data", {}).get("flow_type")
                if not flow_type and "_previous_data" in flow_data:
                    flow_type = flow_data["_previous_data"].get("flow_type")

            # Build new state with member-centric structure
            new_state = {
                # Core identity - SINGLE SOURCE OF TRUTH
                "member_id": current_state.get("member_id"),  # Primary identifier

                # Channel information - maintain existing channel info unless explicitly updated
                "channel": StateManager.create_channel_data(
                    identifier=channel_identifier if channel_identifier is not None else StateManager.get_channel_identifier(current_state),
                    channel_type=StateManager.get_channel_type(current_state)
                ),

                # Authentication and account
                "account_id": current_state.get("account_id"),
                "jwt_token": current_state.get("jwt_token"),
                "authenticated": current_state.get("authenticated", False),

                # Flow and profile data
                "flow_data": flow_data,
                "profile": StateValidator.ensure_profile_structure(current_state.get("profile", {})),
                "flow_type": flow_type,  # Preserve flow type at root level

                # Metadata
                "_last_updated": audit.get_current_timestamp()
            }

            # Ensure parent service is preserved in flow data
            if parent_service and isinstance(flow_data, dict):
                flow_data["_parent_service"] = parent_service

            # Ensure flow type is preserved in flow data (but not member_id)
            if flow_type and isinstance(flow_data, dict):
                if "data" not in flow_data:
                    flow_data["data"] = {}
                flow_data["data"]["flow_type"] = flow_type

            # Ensure member_id is not duplicated in flow_data.data
            if isinstance(flow_data, dict) and isinstance(flow_data.get("data"), dict):
                flow_data["data"].pop("member_id", None)  # Remove if present

            # Update channel metadata if needed
            if channel_identifier is not None and isinstance(new_state["channel"], dict):
                new_state["channel"]["identifier"] = channel_identifier

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
        channel_identifier: str
    ) -> Optional[WhatsAppMessage]:
        """Validate and update state with proper error handling"""
        try:
            # Log state before update
            logger.debug("State before update:")
            logger.debug(f"- Current state: {current_state}")
            logger.debug(f"- New state: {new_state}")
            logger.debug(f"- Operation: {operation}")

            # Start atomic update
            audit.log_flow_event(
                "bot_service",
                "state_update_start",
                operation,
                new_state,
                "in_progress"
            )

            # Ensure channel info is present
            if "channel" not in new_state or not isinstance(new_state["channel"], dict):
                new_state["channel"] = StateManager.create_channel_data(
                    identifier=channel_identifier,
                    channel_type="whatsapp"
                )
                logger.debug("Added missing channel info to new state")

            # Preserve critical fields from current state if missing in new state
            critical_fields = ["jwt_token", "member_id", "account_id", "authenticated"]
            for field in critical_fields:
                if field not in new_state and field in current_state:
                    new_state[field] = current_state[field]
                    logger.debug(f"Preserved {field} from current state")

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                logger.error(f"State validation failed: {validation.error_message}")
                logger.debug(f"Invalid state: {new_state}")
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    operation,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    channel_identifier,
                    f"Failed to update state: {validation.error_message}"
                )

            try:
                # Attempt state update
                state_manager.update_state(new_state, operation)

                # Log state after update
                logger.debug("State after update:")
                logger.debug(f"- Updated state: {state_manager.state}")
                logger.debug(f"- Has jwt_token: {bool(state_manager.jwt_token)}")

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
                # Log detailed error info
                logger.error(f"State update error: {str(update_error)}")
                logger.debug("Error context:")
                logger.debug(f"- Operation: {operation}")
                logger.debug(f"- Current state: {current_state}")
                logger.debug(f"- Attempted new state: {new_state}")

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
                channel_identifier,
                f"❌ Failed to update state: {str(e)}"
            )
