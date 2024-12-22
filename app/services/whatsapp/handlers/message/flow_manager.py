"""Flow initialization and management"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger

from ...state_manager import StateManager
from ...types import WhatsAppMessage
from ..credex import CredexFlow
from ..member import RegistrationFlow, UpgradeFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class FlowManager:
    """Handles flow initialization and management"""

    def __init__(self, service: Any):
        self.service = service

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state if needed"""
        state = self.service.user.state.state

        # If state is not a dict, initialize it
        if not isinstance(state, dict):
            initial_state = {
                "mobile_number": self.service.user.mobile_number,
                "_last_updated": datetime.now().isoformat(),
                "profile": {
                    "action": {
                        "id": "",
                        "type": "",
                        "timestamp": "",
                        "actor": "",
                        "details": {},
                        "message": "",
                        "status": ""
                    },
                    "dashboard": {
                        "member": {},
                        "accounts": []
                    }
                },
                "current_account": {},
                "jwt_token": None,
                "member_id": None,
                "account_id": None,
                "authenticated": False,
                "_validation_context": {},
                "_validation_state": {}
            }
            self.service.user.state.update_state(initial_state, "init")
            return initial_state
        return state

    def _get_member_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract member and account IDs from state"""
        try:
            state = self._initialize_state()
            member_id = state.get("member_id")
            account_id = state.get("account_id")
            return member_id, account_id
        except Exception as e:
            logger.error(f"Error extracting member info: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "member_info_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return None, None

    def initialize_flow(self, flow_type: str, flow_class: Any, **kwargs) -> WhatsAppMessage:
        """Initialize a new flow"""
        try:
            # Log flow start attempt
            audit.log_flow_event(
                "bot_service",
                "flow_start_attempt",
                None,
                {
                    "flow_type": flow_type,
                    "flow_class": flow_class.__name__ if hasattr(flow_class, '__name__') else str(flow_class),
                    **kwargs
                },
                "in_progress"
            )

            # Get member and account IDs
            member_id, account_id = self._get_member_info()
            if not member_id or not account_id:
                logger.error(f"Missing required IDs - member_id: {member_id}, account_id: {account_id}")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "Account not properly initialized. Please try sending 'hi' to restart."
                )

            # Get current state
            current_state = self._initialize_state()

            # Initialize state with required fields
            initial_data = {
                "phone": self.service.user.mobile_number,
                "member_id": member_id,
                "account_id": account_id,
                "mobile_number": self.service.user.mobile_number,
                "flow_type": flow_type,  # Always include flow type
                "_validation_context": current_state.get("_validation_context", {}),  # Preserve validation context
                "_validation_state": current_state.get("_validation_state", {})      # Preserve validation state
            }

            # Add current account data for action flows
            if flow_type in ["cancel", "accept", "decline"]:
                initial_data["current_account"] = current_state.get("current_account", {})

            # Create complete initial state
            initial_state = {
                "id": f"{flow_type}_{member_id}",
                "step": 0,
                "data": initial_data,
                "_previous_data": initial_data.copy(),  # Ensure previous data is initialized
                "_validation_context": current_state.get("_validation_context", {}),  # Preserve at top level
                "_validation_state": current_state.get("_validation_state", {})      # Preserve at top level
            }

            # Initialize flow with state
            flow = self._create_flow(flow_type, flow_class, initial_state, **kwargs)
            flow.credex_service = self.service.credex_service

            # Get initial message
            if flow.current_step:
                result = flow.current_step.get_message(flow.data)
            else:
                result = WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "Flow not properly initialized"
                )

            # If result is a WhatsAppMessage, return it immediately
            if isinstance(result, WhatsAppMessage):
                return result

            # Update state only for non-WhatsAppMessage responses
            self._update_flow_state(flow, flow_type, flow_class, kwargs)

            audit.log_flow_event(
                "bot_service",
                "flow_start_success",
                None,
                {"flow_id": flow.id},
                "success"
            )

            return result

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "flow_start_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                f"❌ Failed to start flow: {str(e)}"
            )

    def _get_pending_offers(self) -> Dict[str, Any]:
        """Get current account with pending offers"""
        state = self._initialize_state()
        return state.get("current_account", {})

    def _create_flow(self, flow_type: str, flow_class: Any, initial_state: Dict, **kwargs) -> Flow:
        """Create flow instance with proper initialization"""
        if flow_class in {RegistrationFlow, UpgradeFlow}:
            return flow_class(**kwargs)

        # Initialize flow with state
        flow_kwargs = kwargs.copy()  # Create a copy to avoid modifying original kwargs
        if flow_class == CredexFlow:
            flow_kwargs['flow_type'] = flow_type
        return flow_class(
            state=initial_state,
            **flow_kwargs
        )

    def _update_flow_state(self, flow: Flow, flow_type: str, flow_class: Any, kwargs: Dict):
        """Update state with flow data"""
        current_state = self._initialize_state()

        # Store the modified kwargs in state
        flow_kwargs = kwargs.copy()
        if flow_class == CredexFlow:
            flow_kwargs['flow_type'] = flow_type

        new_state = StateManager.prepare_state_update(
            current_state,
            flow_data={
                **flow.get_state(),
                "flow_type": flow_type,
                "kwargs": flow_kwargs
            },
            mobile_number=self.service.user.mobile_number
        )

        # Validate and update state
        error = StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "flow_start",
            self.service.user.mobile_number
        )
        if error:
            raise ValueError(f"State update failed: {error}")
