"""State management for WhatsApp service"""
import logging
from typing import Any, Dict, Optional

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from .types import WhatsAppMessage

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateManager:
    """Helper class for managing state transitions"""

    @staticmethod
    def get_channel_identifier(state: Dict[str, Any]) -> Optional[str]:
        """Get channel identifier from state following SINGLE SOURCE OF TRUTH"""
        try:
            return state.get("channel", {}).get("identifier")
        except Exception as e:
            logger.error(f"Error getting channel identifier: {str(e)}")
            return None

    @staticmethod
    def get_channel_type(state: Dict[str, Any]) -> Optional[str]:
        """Get channel type from state following SINGLE SOURCE OF TRUTH"""
        try:
            return state.get("channel", {}).get("type")
        except Exception as e:
            logger.error(f"Error getting channel type: {str(e)}")
            return None

    @staticmethod
    def get_member_id(state: Dict) -> Optional[str]:
        """Get member ID from state following single source of truth"""
        return state.get("member_id") if state else None

    @staticmethod
    def prepare_state_update(
        current_state: Dict[str, Any],
        flow_data: Optional[Dict[str, Any]] = None,
        channel_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare state update maintaining SINGLE SOURCE OF TRUTH"""
        try:
            # Create new state
            new_state = {
                # Top level identity and auth
                "member_id": current_state.get("member_id"),
                "account_id": current_state.get("account_id"),
                "jwt_token": current_state.get("jwt_token"),
                "authenticated": current_state.get("authenticated", False),

                # Channel info at top level
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_identifier or current_state.get("channel", {}).get("identifier")
                },

                # Profile data
                "profile": current_state.get("profile", {}),

                # Flow data
                "flow_data": flow_data if flow_data is not None else {
                    "step": 0,
                    "flow_type": "auth"
                },

                # Metadata
                "_last_updated": audit.get_current_timestamp()
            }

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
        """Validate and update state"""
        try:
            # Preserve critical fields from current state
            for field in ["jwt_token", "member_id", "account_id", "authenticated"]:
                if field not in new_state and field in current_state:
                    new_state[field] = current_state[field]

            # Validate state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                logger.error(f"State validation failed: {validation.error_message}")
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

            # Update state
            state_manager.update_state(new_state)

            # Log transition
            audit.log_state_transition(
                "bot_service",
                current_state,
                new_state,
                "success"
            )

            return None

        except Exception as e:
            logger.error(f"State update error: {str(e)}")
            return WhatsAppMessage.create_text(
                channel_identifier,
                f"❌ Failed to update state: {str(e)}"
            )
