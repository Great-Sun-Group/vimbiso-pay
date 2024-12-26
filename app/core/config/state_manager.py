"""Core state management functionality"""
import logging
from typing import Any, Dict

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from services.credex.service import CredExService

from .config import ACTIVITY_TTL, atomic_state
from .state_utils import (create_initial_state, prepare_state_update,
                          update_critical_fields)

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class StateManager:
    """Manages atomic state operations"""
    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix
        self.state = None
        self.jwt_token = None
        self._initialize_state()
        self._credex_service = None

    def _initialize_state(self) -> None:
        """Initialize state with atomic operations"""
        state_data, _ = atomic_state.atomic_get(self.key_prefix)
        if not state_data:
            state_data = create_initial_state()

        validation = StateValidator.validate_state(state_data)
        if not validation.is_valid:
            last_valid = audit.get_last_valid_state("user_state")
            state_data = last_valid if last_valid else create_initial_state()

        self.state = state_data
        self.jwt_token = state_data.get("jwt_token")
        atomic_state.atomic_update(self.key_prefix, state_data, ACTIVITY_TTL)

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with new values"""
        try:
            new_state = update_critical_fields(self.state.copy(), updates)
            new_state = prepare_state_update(new_state, updates)

            if atomic_state.atomic_update(self.key_prefix, new_state, ACTIVITY_TTL)[0]:
                self.state = new_state
                self.jwt_token = new_state.get("jwt_token")
                if self._credex_service:
                    self._update_service_token(self.jwt_token)
        except Exception:
            logger.exception("State update error")

    def get_or_create_credex_service(self) -> CredExService:
        """Get or create CredEx service instance"""
        if not self._credex_service:
            self._credex_service = CredExService(user=self)
            if self.jwt_token:
                self._update_service_token(self.jwt_token)
        return self._credex_service

    def _update_service_token(self, jwt_token: str) -> None:
        """Update service token"""
        if not self._credex_service:
            return
        self._credex_service._jwt_token = jwt_token
        for service in ['_auth', '_member', '_offers', '_recurring']:
            if hasattr(self._credex_service, service):
                setattr(getattr(self._credex_service, service), '_jwt_token', jwt_token)

    def cleanup(self, preserve_fields: set = None) -> bool:
        """Clean up state preserving specified fields"""
        preserve_fields = preserve_fields or {"jwt_token", "member_id", "account_id"}
        success, _ = atomic_state.atomic_cleanup(self.key_prefix, preserve_fields)
        if success:
            self._initialize_state()
        return success
