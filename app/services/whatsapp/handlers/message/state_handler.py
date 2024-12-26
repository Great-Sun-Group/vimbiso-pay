"""State handling and transitions for WhatsApp flows"""
import logging
from typing import Any, Dict, Optional

from core.messaging.flow import Flow, FlowState
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...types import WhatsAppMessage
from ...state_manager import StateManager as WhatsAppStateManager

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateHandler:
    """Handles state management and transitions"""

    def __init__(self, service: Any):
        self.service = service

    def prepare_flow_start(
        self,
        clear_menu: bool = True,
        is_greeting: bool = False,
        flow_type: Optional[str] = None,
        channel_identifier: Optional[str] = None,
        **kwargs
    ) -> Optional[WhatsAppMessage]:
        """Prepare state for starting a new flow"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Log existing state info
            existing_member_id = current_state.get("member_id")
            existing_account_id = current_state.get("account_id")
            existing_jwt = current_state.get("jwt_token")

            logger.debug("Existing state data:")
            logger.debug(f"- Member ID: {existing_member_id}")
            logger.debug(f"- Account ID: {existing_account_id}")
            logger.debug(f"- Has JWT: {bool(existing_jwt)}")

            # Prepare base state
            base_state = {
                # Preserve existing fields
                "member_id": existing_member_id,
                "account_id": existing_account_id,
                "jwt_token": existing_jwt,
                "authenticated": current_state.get("authenticated", False),

                # Channel info - SINGLE SOURCE OF TRUTH
                "channel": WhatsAppStateManager.create_channel_data(
                    identifier=channel_identifier or self.service.user.channel_identifier,
                    channel_type="whatsapp"
                ),

                # Profile and accounts
                "profile": current_state.get("profile", {}),
                "current_account": current_state.get("current_account", {}),

                # Version and audit
                "_last_updated": audit.get_current_timestamp()
            }

            # Only require member_id for non-greeting flows
            member_id = current_state.get("member_id")
            if not is_greeting and not member_id:
                return WhatsAppMessage.create_text(
                    self.service.user.channel_identifier,
                    "❌ Error: Member ID not found"
                )

            # Create flow state with proper initialization
            flow_state = FlowState.create(
                flow_id=f"{flow_type}_{member_id}" if member_id and flow_type else "user_state",
                member_id=member_id or "pending",  # Use "pending" if no member_id yet
                flow_type=flow_type or "init"
            )

            # Preserve validation context if exists
            flow_data = current_state.get("flow_data", {})
            if isinstance(flow_data, dict) and isinstance(flow_data.get("data"), dict):
                validation_context = {
                    k: v for k, v in flow_data["data"].items()
                    if k in ("_validation_context", "_validation_state")
                }
                flow_state.data.update(validation_context)

            # Build new state preserving SINGLE SOURCE OF TRUTH
            new_state = {
                **base_state,
                "flow_data": flow_state.to_dict()
            }

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                logger.error(f"Invalid state: {validation.error_message}")
                return WhatsAppMessage.create_text(
                    self.service.user.channel_identifier,
                    f"❌ Error: {validation.error_message}"
                )

            # Update state
            self.service.user.state.update_state(new_state, "flow_start")

            # Log state update details
            logger.debug("State update details:")
            logger.debug(f"- Channel ID matches: {new_state.get('channel', {}).get('identifier') == channel_identifier}")
            logger.debug(f"- Preserved member ID: {new_state.get('member_id') == existing_member_id}")
            logger.debug(f"- Preserved JWT: {new_state.get('jwt_token') == existing_jwt}")

            return None

        except Exception as e:
            logger.error(f"Error preparing flow start: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_flow_completion(self, clear_flow: bool = True) -> Optional[WhatsAppMessage]:
        """Handle flow completion state update"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Preserve validation context
            validation_context = {
                k: v for k, v in current_state.get("flow_data", {}).items()
                if k.startswith("_")
            }

            # Prepare state update
            new_state = WhatsAppStateManager.prepare_state_update(
                current_state,
                flow_data=validation_context if validation_context else None,
                clear_flow=True,
                preserve_validation=True
            )

            # Update state
            self.service.user.state.update_state(new_state, "flow_complete")

            return None

        except Exception as e:
            logger.error(f"Error handling flow completion: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_flow_continuation(
        self,
        flow: Flow,
        flow_type: str,
        kwargs: Dict[str, Any]
    ) -> Optional[WhatsAppMessage]:
        """Handle flow continuation state update"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Get member ID from current state - SINGLE SOURCE OF TRUTH
            member_id = current_state.get("member_id")
            if not member_id:
                raise ValueError("Member ID not found in state")

            # Get flow state
            flow_state = flow.get_state()

            # Create new FlowState from flow state
            new_flow_state = FlowState.from_dict(flow_state, member_id)

            # Build new state preserving SINGLE SOURCE OF TRUTH
            new_state = WhatsAppStateManager.prepare_state_update(
                current_state,
                flow_data=new_flow_state.to_dict(),
                preserve_validation=True
            )

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                logger.error(f"Invalid state: {validation.error_message}")
                return WhatsAppMessage.create_text(
                    self.service.user.channel_identifier,
                    f"❌ Error: {validation.error_message}"
                )

            # Update state
            self.service.user.state.update_state(new_state, "flow_continue")

            return None

        except Exception as e:
            logger.error(f"Error handling flow continuation: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_error_state(self, error_message: str) -> WhatsAppMessage:
        """Handle error state and return error message"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Get member ID from state
            member_id = current_state.get("member_id", "pending")

            # Log error with context
            audit.log_flow_event(
                "bot_service",
                "error_state",
                None,
                {
                    "error": error_message,
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.service.user.channel_identifier
                    }
                },
                "failure"
            )

            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {error_message}"
            )

        except Exception as e:
            logger.error(f"Error handling error state: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def handle_invalid_input_state(
        self,
        error_message: str,
        flow_step_id: Optional[str] = None
    ) -> WhatsAppMessage:
        """Handle invalid input state and return error message"""
        try:
            # Get current state
            current_state = self.service.user.state.state or {}

            # Get member ID from state
            member_id = current_state.get("member_id", "pending")

            # Log error with context
            audit.log_flow_event(
                "bot_service",
                "invalid_input",
                flow_step_id,
                {
                    "error": error_message,
                    "member_id": member_id,
                    "channel": {
                        "type": "whatsapp",
                        "identifier": self.service.user.channel_identifier
                    }
                },
                "failure"
            )

            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Invalid input: {error_message}"
            )

        except Exception as e:
            logger.error(f"Error handling invalid input: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.channel_identifier,
                f"❌ Error: {str(e)}"
            )

    def get_flow_data(self) -> Optional[Dict]:
        """Get current flow data from state"""
        state = self.service.user.state.state
        if not state or not isinstance(state, dict):
            return None

        return self.service.user.state.state.get("flow_data")
