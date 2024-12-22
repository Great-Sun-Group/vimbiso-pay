"""Flow initialization and management"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger

from ...state_manager import StateManager
from ...types import WhatsAppMessage
from ..credex.flows import CredexFlow
from ..member.registration import RegistrationFlow
from ..member.upgrade import UpgradeFlow

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
        """Extract member and account IDs"""
        try:
            state = self._initialize_state()
            member_id = state.get("data", {}).get("member_id")
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

            # Get current state first
            current_state = self._initialize_state()

            # Get member ID from top level
            member_id = kwargs.get("member_id")
            if not member_id:
                logger.error("Missing member ID")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "❌ Failed to start flow: Missing member ID"
                )

            # Get account ID from state for backward compatibility
            account_id = current_state.get("account_id")
            if not account_id:
                logger.error("Missing account ID")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "Account not properly initialized. Please try sending 'hi' to restart."
                )

            # Log flow initialization
            logger.debug(f"Initializing flow {flow_type} with member_id {member_id}")

            # Initialize state with required fields
            initial_data = {
                "phone": self.service.user.mobile_number,
                "member_id": member_id,
                "account_id": account_id,
                "mobile_number": self.service.user.mobile_number,
                "flow_type": flow_type,  # Always include flow type
                "_validation_context": current_state.get("_validation_context", {}),
                "_validation_state": current_state.get("_validation_state", {})
            }

            # Log initial data
            logger.debug(f"Initial data prepared: {initial_data}")

            # Add current account data for action flows
            if flow_type in ["cancel", "accept", "decline"]:
                initial_data["current_account"] = current_state.get("current_account", {})

            # Create complete initial state
            initial_state = {
                "id": f"{flow_type}_{member_id}",
                "step": 0,
                "data": initial_data,
                "_previous_data": initial_data.copy(),
                "_validation_context": current_state.get("_validation_context", {}),
                "_validation_state": current_state.get("_validation_state", {})
            }

            # Log flow initialization details
            logger.debug("Flow initialization details:")
            logger.debug(f"- Flow type: {flow_type}")
            logger.debug(f"- Flow ID: {initial_state['id']}")
            logger.debug(f"- Initial data: {initial_data}")

            # Add parent service to initial state
            initial_state["flow_data"] = {
                **initial_state,
                "_parent_service": self.service
            }

            # Initialize flow with state
            flow = self._create_flow(flow_type, flow_class, initial_state, **kwargs)
            flow.credex_service = self.service.credex_service

            # Update state first
            logger.debug("[FlowManager] Pre-update flow state:")
            logger.debug("- Flow type: %s", flow_type)
            logger.debug("- Flow data: %s", flow.get_state().get("flow_data"))
            logger.debug("- Parent service: %s", self.service)

            self._update_flow_state(flow, flow_type, flow_class, kwargs)

            logger.debug("[FlowManager] Post-update flow state:")
            logger.debug("- Updated state: %s", self.service.user.state.state)

            # Get initial message after state is updated
            if flow.current_step:
                result = flow.current_step.get_message(flow.data)
            else:
                result = WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "Flow not properly initialized"
                )

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

        # Get flow state and ensure it has required structure
        flow_state = flow.get_state()
        flow_data = {
            "id": flow_state.get("id") or f"{flow_type}_{self.service.user.mobile_number}",
            "step": flow_state.get("step", 0),
            "data": {
                **(flow_state.get("data", {})),
                "mobile_number": self.service.user.mobile_number,
                "flow_type": flow_type
            },
            "_previous_data": flow_state.get("_previous_data", {})
        }

        # Store the modified kwargs and parent service in flow data
        flow_kwargs = kwargs.copy()
        if flow_class == CredexFlow:
            flow_kwargs['flow_type'] = flow_type
        flow_data.update({
            "kwargs": flow_kwargs,
            "_parent_service": self.service  # Ensure parent service is preserved
        })

        new_state = StateManager.prepare_state_update(
            current_state,
            flow_data=flow_data,
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
