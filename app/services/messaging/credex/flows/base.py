"""Base flow class with common functionality

This module provides the base flow class with:
- Pure UI validation in components
- Business logic in services
- Flow coordination with proper state management
- Clear validation boundaries
"""

import logging
from typing import Any, Dict, Optional, Type

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException
from core.utils.error_handler import ErrorHandler
from core.components.base import Component

logger = logging.getLogger(__name__)


class CredexFlow:
    """Base class for credex-related flows with proper state management"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service
        self.components: Dict[str, Component] = {}

    def get_step_content(self, step: str, data: Optional[Dict] = None) -> str:
        """Get step content without channel formatting"""
        raise NotImplementedError("Flow must implement get_step_content")

    def process_step(self, state_manager: Any, step: str, input_value: Any) -> Message:
        """Process flow step using messaging service"""
        raise NotImplementedError("Flow must implement process_step")

    def _get_recipient(self, state_manager: Any) -> MessageRecipient:
        """Get message recipient from state"""
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=state_manager.get("member_id")
        )

    def _get_component(self, component_type: Type[Component], **kwargs) -> Component:
        """Get or create component with proper state tracking"""
        component_name = component_type.__name__
        if component_name not in self.components:
            self.components[component_name] = component_type(**kwargs)
        return self.components[component_name]

    def _validate_input(
        self,
        state_manager: Any,
        step: str,
        input_value: Any,
        component: Component
    ) -> Dict:
        """Validate input with proper state tracking

        Args:
            state_manager: State manager instance
            step: Current step
            input_value: Input to validate
            component: Component to use for validation

        Returns:
            Dict with validation result

        Raises:
            FlowException: If validation fails
        """
        try:
            # UI validation
            validation = component.validate(input_value)
            if not validation.valid:
                error_response = ErrorHandler.handle_component_error(
                    component=component.type,
                    field=validation.error.get("field", "value"),
                    value=input_value,
                    message=validation.error.get("message", "Invalid input"),
                    validation_state=component.validation_state
                )
                raise FlowException(
                    message=error_response["error"]["message"],
                    step=step,
                    action="validate",
                    data=error_response["error"]["details"]
                )

            # Update component state
            state_manager.update_state({
                "flow_data": {
                    "active_component": component.get_ui_state()
                }
            })

            return validation.value

        except FlowException:
            raise

        except Exception as e:
            error_response = ErrorHandler.handle_system_error(
                code="VALIDATION_ERROR",
                service="credex_flow",
                action=f"validate_{step}",
                message=str(e),
                error=e
            )
            raise FlowException(
                message=error_response["error"]["message"],
                step=step,
                action="validate",
                data=error_response["error"]["details"]
            )

    def _update_flow_data(
        self,
        state_manager: Any,
        updates: Dict[str, Any]
    ) -> None:
        """Update flow data with validation

        Args:
            state_manager: State manager instance
            updates: Data updates to apply

        Raises:
            FlowException: If update fails
        """
        try:
            # Get current data
            flow_data = state_manager.get_flow_data()

            # Update with new data
            state_manager.update_state({
                "flow_data": {
                    "data": {
                        **flow_data,
                        **updates
                    }
                }
            })

        except Exception as e:
            error_response = ErrorHandler.handle_system_error(
                code="STATE_UPDATE_ERROR",
                service="credex_flow",
                action="update_flow_data",
                message=str(e),
                error=e
            )
            raise FlowException(
                message=error_response["error"]["message"],
                step="update",
                action="update_data",
                data=error_response["error"]["details"]
            )
