"""WhatsApp state management delegating to core StateManager"""
import logging
from typing import Any, Dict, Optional

from core.error.exceptions import SystemException
from core.messaging.interface import MessagingServiceInterface
from core.state.interface import StateManagerInterface
from core.state.manager import StateManager as CoreStateManager

logger = logging.getLogger(__name__)


class StateManager(StateManagerInterface):  # type: ignore
    """WhatsApp state management delegating to core StateManager"""

    def __init__(self, state_manager: CoreStateManager):
        """Initialize with core state manager"""
        self._core = state_manager

    @property
    def messaging(self) -> MessagingServiceInterface:
        """Get messaging service"""
        return self._core.messaging

    @messaging.setter
    def messaging(self, service: MessagingServiceInterface) -> None:
        """Set messaging service"""
        self._core.messaging = service

    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get state value using core state manager"""
        try:
            return self._core.get_state_value(key, default)
        except Exception as e:
            raise SystemException(
                message=f"Failed to get state value for key: {key}",
                code="STATE_GET_ERROR",
                service="whatsapp_state",
                action="get_state",
                details={
                    "key": key,
                    "error": str(e)
                }
            )

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state using core state manager"""
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Updating state")
            self._core.update_state(updates)
        except Exception as e:
            raise SystemException(
                message="Failed to update state",
                code="STATE_UPDATE_ERROR",
                service="whatsapp_state",
                action="update_state",
                details={
                    "update_keys": list(updates.keys()),
                    "error": str(e)
                }
            )

    def get_path(self) -> Optional[str]:
        """Get current flow path"""
        return self._core.get_path()

    def get_component(self) -> Optional[str]:
        """Get current component"""
        return self._core.get_component()

    def get_component_result(self) -> Optional[str]:
        """Get component result for flow branching"""
        return self._core.get_component_result()

    def is_awaiting_input(self) -> bool:
        """Check if component is waiting for input"""
        return self._core.is_awaiting_input()

    def update_component_data(
        self,
        path: str,
        component: str,
        data: Optional[Dict] = None,
        component_result: Optional[str] = None,
        awaiting_input: bool = False
    ) -> None:
        """Update current flow/component state"""
        self._core.update_component_data(
            path=path,
            component=component,
            data=data,
            component_result=component_result,
            awaiting_input=awaiting_input
        )

    def clear_component_data(self) -> None:
        """Clear flow/component state"""
        self._core.clear_component_data()

    def clear_all_state(self) -> None:
        """Clear all state data except channel info"""
        self._core.clear_all_state()

    def get_channel_id(self) -> str:
        """Get channel identifier"""
        return self._core.get_channel_id()

    def get_channel_type(self) -> str:
        """Get channel type"""
        return self._core.get_channel_type()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token"""
        return self._core.is_authenticated()

    def get_member_id(self) -> Optional[str]:
        """Get member ID if authenticated"""
        return self._core.get_member_id()

    def is_mock_testing(self) -> bool:
        """Check if mock testing mode is enabled"""
        return self._core.is_mock_testing()
