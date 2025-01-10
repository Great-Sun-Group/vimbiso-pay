"""WhatsApp state management delegating to core StateManager"""
import logging
from typing import Any, Dict, Optional

from core.error.exceptions import SystemException
from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import ChannelType
from core.state.interface import StateManagerInterface
from core.state.manager import StateManager as CoreStateManager

logger = logging.getLogger(__name__)


class StateManager(StateManagerInterface):  # type: ignore
    """WhatsApp state management delegating to core StateManager"""

    def __init__(self, state_manager: CoreStateManager):
        """Initialize with core state manager

        Args:
            state_manager: Core state manager instance

        Raises:
            SystemException: If state manager is not properly initialized
        """
        if not state_manager:
            raise SystemException(
                message="Core state manager is required: state_manager is None",
                code="STATE_INIT_ERROR",
                service="whatsapp_state",
                action="initialize"
            )

        if not isinstance(state_manager, CoreStateManager):
            raise SystemException(
                message=f"Invalid core state manager type: expected {CoreStateManager.__name__}, got {type(state_manager).__name__}",
                code="STATE_INIT_ERROR",
                service="whatsapp_state",
                action="initialize"
            )

        self._core = state_manager

    @property
    def messaging(self) -> MessagingServiceInterface:
        """Get messaging service"""
        try:
            return self._core.messaging
        except Exception as e:
            raise SystemException(
                message=f"Failed to get messaging service: {str(e)}",
                code="MESSAGING_ERROR",
                service="whatsapp_state",
                action="get_messaging"
            )

    @messaging.setter
    def messaging(self, service: MessagingServiceInterface) -> None:
        """Set messaging service"""
        try:
            self._core.messaging = service
        except Exception as e:
            raise SystemException(
                message=f"Failed to set messaging service: {str(e)}",
                code="MESSAGING_ERROR",
                service="whatsapp_state",
                action="set_messaging"
            )

    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get state value using core state manager"""
        try:
            return self._core.get_state_value(key, default)
        except Exception as e:
            raise SystemException(
                message=f"Failed to get state value for key {key}: {str(e)}",
                code="STATE_GET_ERROR",
                service="whatsapp_state",
                action="get_state"
            )

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state using core state manager"""
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Updating state")
            self._core.update_state(updates)
        except Exception as e:
            raise SystemException(
                message=f"Failed to update state with keys {list(updates.keys())}: {str(e)}",
                code="STATE_UPDATE_ERROR",
                service="whatsapp_state",
                action="update_state"
            )

    def get_path(self) -> Optional[str]:
        """Get current flow path"""
        try:
            return self._core.get_path()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get flow path: {str(e)}",
                code="FLOW_PATH_ERROR",
                service="whatsapp_state",
                action="get_path"
            )

    def get_component(self) -> Optional[str]:
        """Get current component"""
        try:
            return self._core.get_component()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get component: {str(e)}",
                code="FLOW_COMPONENT_ERROR",
                service="whatsapp_state",
                action="get_component"
            )

    def get_component_result(self) -> Optional[str]:
        """Get component result for flow branching"""
        try:
            return self._core.get_component_result()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get component result: {str(e)}",
                code="FLOW_RESULT_ERROR",
                service="whatsapp_state",
                action="get_component_result"
            )

    def is_awaiting_input(self) -> bool:
        """Check if component is waiting for input"""
        try:
            return self._core.is_awaiting_input()
        except Exception as e:
            raise SystemException(
                message=f"Failed to check awaiting input: {str(e)}",
                code="FLOW_INPUT_ERROR",
                service="whatsapp_state",
                action="is_awaiting_input"
            )

    def update_flow_state(
        self,
        path: str,
        component: str,
        data: Optional[Dict] = None,
        component_result: Optional[str] = None,
        awaiting_input: bool = False
    ) -> None:
        """Update flow state including path and component

        This is the low-level interface used by the flow processor to manage transitions.
        It requires all schema fields including path and component. Components should
        never use this directly - they should use Component.update_component_data() instead.

        Args:
            path: Current flow path
            component: Current component
            data: Optional component data (unvalidated)
            component_result: Optional result for flow branching
            awaiting_input: Whether component is waiting for input
        """
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Updating flow state")
            self._core.update_flow_state(
                path=path,
                component=component,
                data=data,
                component_result=component_result,
                awaiting_input=awaiting_input
            )
        except Exception as e:
            raise SystemException(
                message=f"Failed to update flow state for {path}.{component}: {str(e)}",
                code="FLOW_STATE_UPDATE_ERROR",
                service="whatsapp_state",
                action="update_flow_state"
            )

    def clear_component_data(self) -> None:
        """Clear flow/component state"""
        try:
            self._core.clear_component_data()
        except Exception as e:
            raise SystemException(
                message=f"Failed to clear component data: {str(e)}",
                code="STATE_CLEAR_ERROR",
                service="whatsapp_state",
                action="clear_component_data"
            )

    def clear_all_state(self) -> None:
        """Clear all state data except channel info"""
        try:
            self._core.clear_all_state()
        except Exception as e:
            raise SystemException(
                message=f"Failed to clear all state: {str(e)}",
                code="STATE_CLEAR_ERROR",
                service="whatsapp_state",
                action="clear_all_state"
            )

    def get_channel_id(self) -> str:
        """Get channel identifier"""
        try:
            return self._core.get_channel_id()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get channel ID: {str(e)}",
                code="CHANNEL_ERROR",
                service="whatsapp_state",
                action="get_channel_id"
            )

    def get_channel_type(self) -> ChannelType:
        """Get channel type"""
        try:
            return self._core.get_channel_type()  # Returns ChannelType enum
        except Exception as e:
            raise SystemException(
                message=f"Failed to get channel type: {str(e)}",
                code="CHANNEL_ERROR",
                service="whatsapp_state",
                action="get_channel_type"
            )

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token"""
        try:
            return self._core.is_authenticated()
        except Exception as e:
            raise SystemException(
                message=f"Failed to check authentication: {str(e)}",
                code="AUTH_ERROR",
                service="whatsapp_state",
                action="is_authenticated"
            )

    def get_member_id(self) -> Optional[str]:
        """Get member ID if authenticated"""
        try:
            return self._core.get_member_id()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get member ID: {str(e)}",
                code="AUTH_ERROR",
                service="whatsapp_state",
                action="get_member_id"
            )

    def is_mock_testing(self) -> bool:
        """Check if mock testing mode is enabled"""
        try:
            return self._core.is_mock_testing()
        except Exception as e:
            raise SystemException(
                message=f"Failed to check mock testing mode: {str(e)}",
                code="STATE_ERROR",
                service="whatsapp_state",
                action="is_mock_testing"
            )

    def initialize_channel(self, channel_type: ChannelType, channel_id: str, mock_testing: bool = False) -> None:
        """Initialize or update channel info"""
        try:
            self._core.initialize_channel(channel_type, channel_id, mock_testing)
        except Exception as e:
            raise SystemException(
                message=f"Failed to initialize channel: {str(e)}",
                code="CHANNEL_ERROR",
                service="whatsapp_state",
                action="initialize_channel"
            )
