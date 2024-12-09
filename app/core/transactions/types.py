from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class TransactionType(Enum):
    """Types of transactions that can be performed"""
    SECURED_CREDEX = "secured_credex"
    UNSECURED_CREDEX = "unsecured_credex"


class TransactionStatus(Enum):
    """Possible states of a transaction"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Account:
    """Account information"""
    id: str
    name: str
    denomination: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionOffer:
    """Transaction offer details"""
    authorizer_member_id: str
    issuer_member_id: str
    amount: float
    currency: str
    type: TransactionType
    handle: Optional[str] = None
    due_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    """Complete transaction information"""
    id: str
    offer: TransactionOffer
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionResult:
    """Result of a transaction operation"""
    success: bool
    transaction: Optional[Transaction] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
