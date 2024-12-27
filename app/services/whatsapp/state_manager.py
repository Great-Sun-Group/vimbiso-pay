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
        validation = StateValidator.validate_before_access(state, {"channel"})
        if not validation.is_valid:
            logger.error(f"State validation failed: {validation.error_message}")
            return None

        return state.get("channel", {}).get("identifier")

    @staticmethod
    def get_channel_type(state: Dict[str, Any]) -> Optional[str]:
        """Get channel type from state following SINGLE SOURCE OF TRUTH"""
        validation = StateValidator.validate_before_access(state, {"channel"})
        if not validation.is_valid:
            logger.error(f"State validation failed: {validation.error_message}")
            return None

        return state.get("channel", {}).get("type")

    @staticmethod
    def get_member_id(state: Dict[str, Any]) -> Optional[str]:
        """Get member ID from state following SINGLE SOURCE OF TRUTH"""
        validation = StateValidator.validate_before_access(state, {"member_id"})
        if not validation.is_valid:
            logger.error(f"State validation failed: {validation.error_message}")
            return None

        return state.get("member_id")

    @staticmethod
    def prepare_state_update(
        current_state: Dict[str, Any],
        flow_data: Optional[Dict[str, Any]] = None,
        channel_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare state update maintaining SINGLE SOURCE OF TRUTH"""
        try:
            # Create new state preserving SINGLE SOURCE OF TRUTH
            # Note: Fields may be None until populated through flows
            new_state = {
                # Core identity (SINGLE SOURCE OF TRUTH)
                "member_id": current_state.get("member_id"),
                "jwt_token": current_state.get("jwt_token"),
                "authenticated": current_state.get("authenticated", False),

                # Channel info (SINGLE SOURCE OF TRUTH)
                "channel": {
                    "type": "whatsapp",
                    "identifier": channel_identifier or current_state.get("channel", {}).get("identifier"),
                    "metadata": current_state.get("channel", {}).get("metadata", {}).copy()
                },

                # Flow data
                "flow_data": flow_data if flow_data is not None else current_state.get("flow_data"),

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
            # Update state (validation handled by state manager)
            success, error = state_manager.update_state(new_state)
            if not success:
                logger.error(f"State update failed: {error}")
                return WhatsAppMessage.create_text(
                    channel_identifier,
                    f"Failed to update state: {error}"
                )

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
