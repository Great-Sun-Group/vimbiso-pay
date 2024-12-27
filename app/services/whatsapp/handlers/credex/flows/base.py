"""Base class for credex flows"""
import logging
from typing import Any, Dict, List

from core.messaging.flow import Flow, Step
from core.utils.flow_audit import FlowAuditLogger

from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class CredexFlow(Flow):
    """Base class for all credex flows"""

    def __init__(
        self,
        id: str,
        steps: List[Step],
        **kwargs
    ) -> None:
        """Initialize credex flow without state duplication"""
        if not id:
            raise ValueError("Flow ID is required")

        # Initialize base Flow class with minimal state
        super().__init__(id=id, steps=steps)

        # Log initialization
        audit.log_flow_event(
            id,
            "initialization",
            None,
            kwargs,
            "success"
        )

    @staticmethod
    def validate_credex_service(credex_service: Any) -> None:
        """Validate service has required capabilities"""
        if not credex_service:
            raise ValueError("Service not initialized")

        if not hasattr(credex_service, 'services'):
            raise ValueError("Service missing required services")

        required_services = {'member', 'offers'}
        missing = required_services - set(credex_service.services.keys())
        if missing:
            raise ValueError(f"Service missing required capabilities: {', '.join(missing)}")

    def process_step_with_state(self, state_manager: Any, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a flow step without state duplication"""
        # Validate state at boundary
        validation_result = StateValidator.validate_state(state_manager)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid state: {validation_result.error_message}")

        # Process step with state manager
        return self.steps[step_data.get("step", 0)].process_with_state(state_manager, step_data)

    def complete_with_state(self, state_manager: Any) -> Dict[str, Any]:
        """Complete flow with state manager - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement complete_with_state()")
