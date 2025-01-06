"""Member operation handlers using clean architecture patterns

Handlers coordinate between flows and services, managing state progression.
"""

import logging
from datetime import datetime
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow
from core.utils.error_handler import ErrorHandler

from .constants import REGISTRATION_NEEDED
from .flows import AuthFlow, RegistrationFlow, UpgradeFlow
from ..utils import get_recipient

logger = logging.getLogger(__name__)


class MemberHandler:
    """Handler for member-related operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service

    def start_registration(self, state_manager: Any) -> Message:
        """Start registration flow with proper state initialization"""
        try:
            # Initialize flow with proper structure
            initialize_flow(
                state_manager=state_manager,
                flow_type="member_registration",
                step="welcome",  # Set initial step properly
                initial_data={
                    "started_at": datetime.utcnow().isoformat()
                }
            )

            # Process welcome step through registration flow
            return RegistrationFlow.process_step(
                messaging_service=self.messaging,
                state_manager=state_manager,
                step="welcome",
                input_value=None
            )

        except Exception as e:
            # Use enhanced error handling
            logger.error("Failed to start registration", extra={
                "error": str(e),
                "handler": "member",
                "action": "start_registration"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="member",
                action="start_registration",
                message="Failed to start registration",
                error=e
            )

            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def start_upgrade(self, state_manager: Any) -> Message:
        """Start upgrade flow with proper state initialization"""
        try:
            # Initialize flow with proper structure
            initialize_flow(
                state_manager=state_manager,
                flow_type="member_upgrade",
                step="confirm",  # Set initial step properly
                initial_data={
                    "started_at": datetime.utcnow().isoformat()
                }
            )

            # Process confirm step through upgrade flow
            return UpgradeFlow.process_step(
                messaging_service=self.messaging,
                state_manager=state_manager,
                step="confirm",
                input_value=None
            )

        except Exception as e:
            # Use enhanced error handling
            logger.error("Failed to start upgrade", extra={
                "error": str(e),
                "handler": "member",
                "action": "start_upgrade"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="member",
                action="start_upgrade",
                message="Failed to start upgrade",
                error=e
            )

            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step with proper error boundaries"""
        try:
            # Get flow state for context
            flow_state = state_manager.get_flow_state()
            if not flow_state:
                raise FlowException(
                    message="No active flow",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

            # Process step through appropriate flow
            if flow_type == "member_auth":
                result = AuthFlow.process_step(self.messaging, state_manager, step, input_value)
                # Handle registration signal
                if result == REGISTRATION_NEEDED:
                    return self.start_registration(state_manager)
                return result
            elif flow_type == "member_registration":
                result = RegistrationFlow.process_step(self.messaging, state_manager, step, input_value)
                return result
            elif flow_type == "member_upgrade":
                result = UpgradeFlow.process_step(self.messaging, state_manager, step, input_value)
                return result
            else:
                raise FlowException(
                    message=f"Invalid flow type: {flow_type}",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

        except FlowException as e:
            # Enhanced flow error handling
            error_response = ErrorHandler.handle_flow_error(
                step=e.details['step'],
                action=e.details['action'],
                data=e.details['data'],
                message=str(e),
                flow_state=flow_state
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except SystemException as e:
            # Enhanced system error handling
            error_response = ErrorHandler.handle_system_error(
                code=e.details['code'],
                service=e.details['service'],
                action=e.details['action'],
                message=str(e),
                error=e
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except Exception as e:
            # Enhanced unexpected error handling
            error_response = ErrorHandler.handle_system_error(
                code="UNEXPECTED_ERROR",
                service="member",
                action="handle_flow",
                message=f"Unexpected error in {flow_type} flow",
                error=e
            )
            return self.messaging.send_text(
                recipient=get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )
