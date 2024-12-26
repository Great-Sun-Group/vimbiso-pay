"""State management and transitions for WhatsApp messages"""
import logging
from typing import Any, Dict, Optional

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...state_manager import StateManager
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateHandler:
    """Handles state management and transitions"""

    def __init__(self, service: Any):
        self.service = service

    def prepare_flow_start(self, clear_menu: bool = True, is_greeting: bool = False, flow_type: Optional[str] = None, **kwargs) -> Optional[WhatsAppMessage]:
        """Prepare state for starting a new flow"""
        current_state = self.service.user.state.state or {}

        # For greetings, initialize state with required fields
        if is_greeting:
            new_state = {
                # Channel info at top level - SINGLE SOURCE OF TRUTH
                "channel": StateManager.create_channel_data(
                    identifier=self.service.user.channel_identifier,
                    channel_type="whatsapp"
                ),

                # Required fields initialized as empty/null
                "member_id": None,
                "account_id": None,
                "profile": StateValidator.ensure_profile_structure({}),
                "authenticated": False,

                # Initialize empty flow data
                "flow_data": {
                    "id": "user_state",
                    "step": 0,
                    "data": {
                        "flow_type": "auth",
                        "_validation_context": {},
                        "_validation_state": {}
                    },
                    "_previous_data": {}
                },
                "_last_updated": audit.get_current_timestamp()
            }
        else:
            # Get channel identifier from top level state
            channel_id = StateManager.get_channel_identifier(current_state)
            if not channel_id:
                # Get channel identifier from user
                channel_id = self.service.user.channel_identifier

            if not flow_type:
                return WhatsAppMessage.create_text(
                    channel_id,
                    "❌ Error: Missing flow type"
                )

            # Get member ID from current state - SINGLE SOURCE OF TRUTH
            member_id = current_state.get("member_id")
            if not member_id:
                return WhatsAppMessage.create_text(
                    channel_id,
                    "❌ Error: Member ID not found in state"
                )

            # Get account ID from state for backward compatibility
            account_id = current_state.get("account_id")
            if not account_id:
                return WhatsAppMessage.create_text(
                    channel_id,
                    "❌ Error: Account not properly initialized"
                )

            # Initialize flow data structure without duplicating channel info
            flow_data = {
                "id": f"{flow_type}_{member_id}",
                "step": 0,
                "data": {
                    "account_id": account_id,
                    "flow_type": flow_type,
                    "_validation_context": {},
                    "_validation_state": {}
                },
                "_previous_data": {}
            }

            # Log flow data for debugging
            logger.debug(f"Creating flow data with type: {flow_type}")
            logger.debug(f"Flow data structure: {flow_data}")

            # Create new state with member-centric structure
            base_state = {
                # Core identity at top level - SINGLE SOURCE OF TRUTH
                "member_id": member_id,  # Primary identifier

                # Channel info at top level - SINGLE SOURCE OF TRUTH
                "channel": StateManager.create_channel_data(
                    identifier=channel_id,
                    channel_type="whatsapp"
                ),

                # Flow and state info
                "flow_type": flow_type,  # Set flow type at root level
                "account_id": current_state.get("account_id"),
                "authenticated": current_state.get("authenticated", False),
                "jwt_token": current_state.get("jwt_token"),
                "_last_updated": audit.get_current_timestamp()
            }

            # Prepare complete state update preserving member_id from current state
            new_state = StateManager.prepare_state_update(
                current_state,
                flow_data=flow_data,
                preserve_validation=True  # Preserve validation to maintain flow data
            )

            # Update with other fields, member_id comes from current state
            new_state.update({k: v for k, v in base_state.items() if k != "member_id"})
            if isinstance(new_state.get("flow_data"), dict):
                new_state["flow_data"]["flow_type"] = flow_type
                if isinstance(new_state["flow_data"].get("data"), dict):
                    new_state["flow_data"]["data"]["flow_type"] = flow_type

        # Log state preparation
        logger.debug("Preparing flow start state:")
        logger.debug(f"- Current state keys: {list(current_state.keys())}")
        logger.debug(f"- New state keys: {list(new_state.keys())}")
        if "flow_data" in new_state:
            logger.debug(f"- Flow data: {new_state['flow_data']}")

        # Get channel identifier from top level state
        channel_id = StateManager.get_channel_identifier(new_state)
        if not channel_id:
            # Get channel identifier from user
            channel_id = self.service.user.channel_identifier

        error = StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "greeting" if is_greeting else ("clear_flow_menu_action" if clear_menu else "flow_start"),
            channel_id
        )
        return error

    def handle_error_state(self, error_message: str) -> WhatsAppMessage:
        """Handle error state and return error message"""
        current_state = self.service.user.state.state or {}

        # Log error details for debugging
        logger.error(f"Flow error state: {error_message}")
        logger.debug(f"Current state: {current_state}")

        # Get channel identifier from top level state
        channel_id = StateManager.get_channel_identifier(current_state)
        if not channel_id:
            # Get channel identifier from user
            channel_id = self.service.user.channel_identifier

        # Preserve validation context
        validation_context = {
            k: v for k, v in current_state.get("flow_data", {}).items()
            if k.startswith("_")
        }
        logger.debug(f"Preserved validation context: {validation_context}")

        # Prepare error state with proper structure
        error_state = StateManager.prepare_state_update(
            current_state,
            flow_data=validation_context if validation_context else None,
            clear_flow=True,
            preserve_validation=True  # Explicitly preserve validation context
        )

        # Ensure channel info is at top level
        error_state["channel"] = StateManager.create_channel_data(
            identifier=channel_id,
            channel_type="whatsapp"
        )

        StateManager.validate_and_update(
            self.service.user.state,
            error_state,
            current_state,
            "flow_error",
            channel_id
        )

        # Return error message
        return WhatsAppMessage.create_text(
            channel_id,
            f"❌ Error: {error_message}"
        )

    def handle_invalid_input_state(
        self,
        flow: Flow,
        flow_type: str,
        kwargs: Dict
    ) -> Optional[WhatsAppMessage]:
        """Handle invalid input state update"""
        current_state = self.service.user.state.state or {}
        flow_state = flow.get_state()

        # Preserve validation context
        validation_context = {
            k: v for k, v in current_state.get("flow_data", {}).items()
            if k.startswith("_")
        }

        # Get member ID from current state - SINGLE SOURCE OF TRUTH
        member_id = current_state.get("member_id")
        if not member_id:
            raise ValueError("Member ID not found in state")

        # Get channel info from top level state
        channel_id = StateManager.get_channel_identifier(current_state)
        if not channel_id:
            raise ValueError("Missing channel identifier")

        # Construct flow data without duplicating channel info
        flow_data = {
            **flow_state,
            "id": f"{flow_type}_{member_id}",  # Ensure consistent ID format
            "flow_type": flow_type,
            "data": {
                **(flow_state.get("data", {}))
            },
            "kwargs": kwargs,
            "_validation_error": True,
            **validation_context  # Restore validation context
        }

        error_state = StateManager.prepare_state_update(
            current_state,
            flow_data=flow_data,
            preserve_validation=True  # Explicitly preserve validation context
        )

        return StateManager.validate_and_update(
            self.service.user.state,
            error_state,
            current_state,
            "flow_validation_error",
            channel_id
        )

    def handle_flow_completion(self, clear_flow: bool = True) -> Optional[WhatsAppMessage]:
        """Handle flow completion state update"""
        current_state = self.service.user.state.state or {}

        # Get channel identifier from top level state
        channel_id = StateManager.get_channel_identifier(current_state)
        if not channel_id:
            raise ValueError("Missing channel identifier")

        # Prepare state update preserving channel info at top level
        new_state = StateManager.prepare_state_update(
            current_state,
            clear_flow=clear_flow,
            preserve_validation=True  # Explicitly preserve validation context
        )

        # Ensure channel info is at top level
        new_state["channel"] = StateManager.create_channel_data(
            identifier=channel_id,
            channel_type="whatsapp"
        )

        return StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "flow_complete",
            channel_id
        )

    def handle_flow_continuation(
        self,
        flow: Flow,
        flow_type: str,
        kwargs: Dict
    ) -> Optional[WhatsAppMessage]:
        """Handle flow continuation state update"""
        current_state = self.service.user.state.state or {}
        flow_state = flow.get_state()

        # Get member ID from current state - SINGLE SOURCE OF TRUTH
        member_id = current_state.get("member_id")
        if not member_id:
            raise ValueError("Member ID not found in state")

        # Get channel info from top level state
        channel_id = StateManager.get_channel_identifier(current_state)
        if not channel_id:
            raise ValueError("Missing channel identifier")

        # Construct flow data without duplicating channel info
        flow_data = {
            **flow_state,
            "id": f"{flow_type}_{member_id}",  # Ensure consistent ID format
            "flow_type": flow_type,
            "data": {
                **(flow_state.get("data", {}))
            },
            "kwargs": kwargs
        }

        # Create base state with member-centric structure
        base_state = {
            # Channel info at top level - SINGLE SOURCE OF TRUTH
            "channel": StateManager.create_channel_data(
                identifier=channel_id,
                channel_type="whatsapp"
            ),

            # Flow and state info
            "flow_type": flow_type,  # Set flow type at root level
            "account_id": current_state.get("account_id"),
            "authenticated": current_state.get("authenticated", False),
            "jwt_token": current_state.get("jwt_token"),
            "_last_updated": audit.get_current_timestamp()
        }

        # Prepare complete state update
        new_state = StateManager.prepare_state_update(
            current_state,
            flow_data=flow_data,
            preserve_validation=True  # Explicitly preserve validation context
        )

        # Ensure flow type is set at all levels
        new_state.update(base_state)
        if isinstance(new_state.get("flow_data"), dict):
            new_state["flow_data"]["flow_type"] = flow_type
            if isinstance(new_state["flow_data"].get("data"), dict):
                new_state["flow_data"]["data"]["flow_type"] = flow_type

        # Log flow continuation state
        logger.debug("Flow continuation state:")
        logger.debug(f"- Flow type: {flow_type}")
        logger.debug(f"- Flow data type: {new_state['flow_data'].get('flow_type')}")
        if isinstance(new_state['flow_data'].get('data'), dict):
            logger.debug(f"- Flow data.data type: {new_state['flow_data']['data'].get('flow_type')}")

        return StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "flow_continue",
            channel_id
        )

    def get_flow_data(self) -> Optional[Dict]:
        """Get current flow data from state"""
        if not self.service.user.state.state:
            return None
        return self.service.user.state.state.get("flow_data")