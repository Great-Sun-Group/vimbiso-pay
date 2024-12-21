"""Interface for flow-specific state validators"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of state validation"""
    is_valid: bool
    error_message: Optional[str] = None
    missing_fields: Set[str] = field(default_factory=set)

    def __bool__(self):
        return self.is_valid


class FlowValidatorInterface(ABC):
    """Interface for flow-specific validators"""

    @abstractmethod
    def validate_flow_data(self, flow_data: Dict[str, Any]) -> ValidationResult:
        """Validate flow-specific data structure"""
        pass

    @abstractmethod
    def validate_flow_state(self, state: Dict[str, Any]) -> ValidationResult:
        """Validate complete flow state"""
        pass

    @abstractmethod
    def get_required_fields(self) -> Set[str]:
        """Get set of required fields for this flow"""
        pass
