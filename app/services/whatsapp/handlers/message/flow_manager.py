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

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from ...types import WhatsAppMessage

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
                - Channel identifier access
                - Channel-specific functionality
        """
        self.service = service

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state if needed or return existing state

        Returns:
            Dict[str, Any]: The initialized or existing state dictionary with:
                - Core identity fields (member_id as primary identifier)
                - Channel information (type and identifier)
                - Profile information
                - Account data
                - Authentication state
                - Validation context
        """
        state = self.service.user.state.state

        # If state is not a dict, initialize fresh state
        if not isinstance(state, dict):
            initial_state = {
                # Core identity
                "member_id": None,
                "account_id": None,

                # Channel information
                "channel": {
                    "type": "whatsapp",
                    "identifier": None,
                    "metadata": {}
                },

                # Profile and accounts
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

                # Authentication
                "jwt_token": None,
                "authenticated": False,

                # Version and audit
                "_last_updated": datetime.now().isoformat(),
                "_validation_context": {},
                "_validation_state": {}
            }

            # Validate initial state
            validation = StateValidator.validate_state(initial_state)
            if not validation.is_valid:
                logger.error(f"Invalid initial state: {validation.error_message}")
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    initial_state,
                    "failure",
                    validation.error_message
                )
            else:
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

            # Check if authenticated
            member_id = current_state.get("member_id")
            if not member_id:
                logger.error("Missing member ID in state")
                return WhatsAppMessage.create_text(
                    current_state.get("channel", {}).get("identifier"),
                    "❌ Failed to start flow: Member ID not found in state"
                )

            # Get account ID from state for backward compatibility
            account_id = current_state.get("account_id")
            if not account_id:
                logger.error("Missing account ID")
                return WhatsAppMessage.create_text(
                    current_state.get("channel", {}).get("identifier"),
                    "Account not properly initialized. Please try sending 'hi' to restart."
                )

            # Log flow initialization
            logger.debug(f"Initializing flow {flow_type} with member_id {member_id}")

            # Create flow ID
            flow_id = f"{flow_type}_{member_id}"

            # Log flow initialization details
            logger.debug("Flow initialization details:")
            logger.debug(f"- Flow type: {flow_type}")
            logger.debug(f"- Flow ID: {flow_id}")
            logger.debug(f"- Member ID: {member_id}")

            # Initialize flow with minimal required state
            flow = flow_class(id=flow_id, steps=[])

            # Set services
            flow.credex_service = self.service.credex_service

            # Get flow state
            flow_data = flow.get_state().to_dict()

            # Build new state preserving SINGLE SOURCE OF TRUTH
            new_state = {
                **current_state,  # Preserve top level state
                "flow_data": flow_data
            }

            # Validate new state
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                logger.error(f"Invalid flow state: {validation.error_message}")
                audit.log_flow_event(
                    "bot_service",
                    "state_validation_error",
                    None,
                    new_state,
                    "failure",
                    validation.error_message
                )
                return WhatsAppMessage.create_text(
                    current_state.get("channel", {}).get("identifier"),
                    f"❌ Failed to initialize flow: {validation.error_message}"
                )

            # Update state
            self.service.user.state.update_state(new_state, "flow_init")

            # Get initial message
            result = (flow.current_step.get_message(flow.data) if flow.current_step
                      else WhatsAppMessage.create_text(
                         current_state.get("channel", {}).get("identifier"),
                         "Flow not properly initialized"
                     ))

            audit.log_flow_event(
                "bot_service",
                "flow_start_success",
                None,
                {"flow_id": flow_id},
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
                self.service.user.state.state.get("channel", {}).get("identifier"),
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
