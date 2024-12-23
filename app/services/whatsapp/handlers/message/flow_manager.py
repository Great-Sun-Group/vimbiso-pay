"""Flow initialization and management for WhatsApp conversations

This module provides the FlowManager class which handles the lifecycle of WhatsApp
conversation flows with member-centric state management. Key features include:

- Member-centric state management with member_id as primary identifier
- Flow initialization and state updates with validation
- Error handling and recovery mechanisms
- Comprehensive audit logging
- State preservation across flow transitions

The module ensures proper state management throughout flow operations while
maintaining member_id at the top level as the single source of truth.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger

from ...state_manager import StateManager
from ...types import WhatsAppMessage
from ..member.registration import RegistrationFlow
from ..member.upgrade import UpgradeFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class FlowManager:
    """Handles WhatsApp flow initialization and state management

    This class manages the lifecycle of WhatsApp conversation flows, including:
        - Flow initialization with proper state management
        - Member-centric state handling (member_id as primary identifier)
        - Flow state updates and validation
        - Error handling and recovery
        - Audit logging of flow events

    The FlowManager ensures that member_id is maintained at the top level
    of state as the single source of truth throughout flow operations.
    """

    def __init__(self, service: Any):
        """Initialize FlowManager with WhatsApp service

        Args:
            service: The WhatsApp service instance that provides:
                - User state management
                - Mobile number access
                - Channel-specific functionality
        """
        self.service = service

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state if needed or return existing state

        Returns:
            Dict[str, Any]: The initialized or existing state dictionary with:
                - Core identity fields (member_id, mobile_number)
                - Profile information
                - Account data
                - Authentication state
                - Validation context
        """
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
        """Extract member and account IDs from state

        Returns:
            Tuple[Optional[str], Optional[str]]: A tuple containing:
                - member_id: The member's unique identifier or None if not found
                - account_id: The account identifier or None if not found

        Note:
            This method gets member_id from the top level of state as the single source of truth.
            Failures are logged and audited before returning None values.
        """
        try:
            state = self._initialize_state()
            # Get member_id from top level only - SINGLE SOURCE OF TRUTH
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
        """Initialize a new flow with proper state management

        Args:
            flow_type: The type of flow to initialize
            flow_class: The class of the flow to create
            **kwargs: Additional keyword arguments passed to flow initialization

        Returns:
            WhatsAppMessage: Success message with initial flow step or error message
        """
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

            # Get member ID from state - SINGLE SOURCE OF TRUTH
            member_id = current_state.get("member_id")
            if not member_id:
                logger.error("Missing member ID in state")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "❌ Failed to start flow: Member ID not found in state"
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

            # Create flow ID
            flow_id = f"{flow_type}_{member_id}"

            # Create initial state with member-centric structure
            initial_state = {
                # Core identity at top level
                "member_id": member_id,  # Primary identifier
                "mobile_number": self.service.user.mobile_number,
                "_last_updated": datetime.now().isoformat(),

                # Flow data with proper structure
                "flow_data": {
                    "id": flow_id,
                    "step": 0,
                    "data": {
                        "mobile_number": self.service.user.mobile_number,
                        "account_id": account_id,
                        "flow_type": flow_type,
                        # Include channel info from kwargs or current state
                        "channel": kwargs.get("channel") or {
                            "type": "whatsapp",
                            "identifier": self.service.user.mobile_number
                        },
                        **({"current_account": current_state.get("current_account", {})}
                           if flow_type in ["cancel", "accept", "decline"] else {})
                    },
                    "_validation_context": current_state.get("_validation_context", {}),
                    "_validation_state": current_state.get("_validation_state", {}),
                    "_parent_service": self.service
                }
            }

            # Log flow initialization details
            logger.debug("Flow initialization details:")
            logger.debug(f"- Flow type: {flow_type}")
            logger.debug(f"- Flow ID: {flow_id}")
            logger.debug(f"- Flow data: {initial_state['flow_data']}")
            logger.debug(f"- Validation context preserved: {bool(initial_state['flow_data'].get('_validation_context'))}")

            # Initialize flow with state
            flow = self._create_flow(flow_type, flow_class, initial_state, **kwargs)
            flow.credex_service = self.service.credex_service

            # Log initialization if flow supports it
            if hasattr(flow, 'log_initialization'):
                flow.log_initialization()

            # Update state first
            logger.debug("[FlowManager] Pre-update flow state:")
            logger.debug("- Flow type: %s", flow_type)
            logger.debug("- Flow data: %s", flow.get_state().get("flow_data"))
            logger.debug("- Parent service: %s", self.service)

            # Update flow state and check for errors
            error = self._update_flow_state(flow, flow_type, flow_class, kwargs)
            if error:
                return error  # Return error message if state update failed

            logger.debug("[FlowManager] Post-update flow state:")
            logger.debug("- Updated state: %s", self.service.user.state.state)

            # Get initial message after successful state update
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
        """Get current account data with pending offers from state

        Returns:
            Dict[str, Any]: The current account dictionary containing:
                - Account information
                - Pending offers data
                - Returns empty dict if no current account exists

        Note:
            This method uses _initialize_state() to ensure state exists
            before attempting to access current_account data.
        """
        state = self._initialize_state()
        return state.get("current_account", {})

    def _create_flow(self, flow_type: str, flow_class: Any, initial_state: Dict, **kwargs) -> Flow:
        """Create flow instance with proper initialization

        Args:
            flow_type: The type of flow to create
            flow_class: The class of the flow to instantiate
            initial_state: The initial state for the flow
            **kwargs: Additional keyword arguments passed to flow initialization

        Returns:
            Flow: The initialized flow instance
        """
        if flow_class in {RegistrationFlow, UpgradeFlow}:
            return flow_class(**kwargs)

        # Initialize flow with state and original kwargs
        return flow_class(
            state=initial_state,
            **kwargs
        )

    def _update_flow_state(
        self,
        flow: Flow,
        flow_type: str,
        flow_class: Any,
        kwargs: Dict
    ) -> Optional[WhatsAppMessage]:
        """Update state with flow data

        Args:
            flow: The flow instance to update state for
            flow_type: The type of flow being managed
            flow_class: The class of the flow
            kwargs: Additional keyword arguments passed to flow initialization

        Returns:
            Optional[WhatsAppMessage]: Returns WhatsAppMessage on error, None on success
        """
        current_state = self._initialize_state()

        try:
            # Get member_id from state - SINGLE SOURCE OF TRUTH
            member_id = current_state.get("member_id")
            if not member_id:
                logger.error("Missing member ID in state")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "❌ Failed to update flow: Member ID not found in state"
                )

            # Get current flow state
            flow_state = flow.get_state()
            flow_id = flow_state.get("id") or f"{flow_type}_{member_id}"

            # Create new state with member-centric structure
            new_state = {
                # Core identity at top level
                "member_id": member_id,  # Primary identifier
                "mobile_number": self.service.user.mobile_number,
                "_last_updated": datetime.now().isoformat(),

                # Flow data with proper structure
                "flow_data": {
                    "id": flow_id,
                    "step": flow_state.get("step", 0),
                    "data": {
                        **(flow_state.get("data", {})),
                        "mobile_number": self.service.user.mobile_number,
                        "flow_type": flow_type,
                        # Preserve channel info from flow data or kwargs
                        "channel": (
                            flow_state.get("data", {}).get("channel") or
                            kwargs.get("channel") or
                            {
                                "type": "whatsapp",
                                "identifier": self.service.user.mobile_number
                            }
                        )
                    },
                    "_previous_data": flow_state.get("_previous_data", {}),
                    "_validation_context": current_state.get("_validation_context", {}),
                    "_validation_state": current_state.get("_validation_state", {}),
                    "_parent_service": self.service,
                    "kwargs": kwargs
                }
            }

            # Update state preserving member_id at top level
            new_state = StateManager.prepare_state_update(
                current_state,
                **new_state  # Pass complete state structure
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
                logger.error(f"State update failed: {error}")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    f"❌ Failed to update flow: {error}"
                )

            return None  # Success case

        except Exception as e:
            logger.error(f"Flow update error: {str(e)}")
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                f"❌ Failed to update flow: {str(e)}"
            )
