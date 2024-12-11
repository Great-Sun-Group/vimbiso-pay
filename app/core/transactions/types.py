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
class Recipient:
    """Transaction recipient information"""
    id: str
    name: str
    handle: str
    last_transaction: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert recipient to dictionary format"""
        return {
            "id": self.id,
            "name": self.name,
            "handle": self.handle,
            "last_transaction": self.last_transaction.isoformat() if self.last_transaction else None,
            "metadata": self.metadata
        }


@dataclass
class TransactionOffer:
    """Transaction offer details"""
    authorizer_member_id: str
    issuer_member_id: str
    amount: float
    denomination: str
    type: TransactionType
    handle: Optional[str] = None
    receiver_account_id: Optional[str] = None
    due_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert offer to dictionary format"""
        return {
            "authorizer_member_id": self.authorizer_member_id,
            "issuer_member_id": self.issuer_member_id,
            "amount": self.amount,
            "denomination": self.denomination,
            "type": self.type.value,
            "handle": self.handle,
            "receiver_account_id": self.receiver_account_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "metadata": self.metadata
        }


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary format"""
        return {
            "id": self.id,
            "offer": self.offer.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class TransactionResult:
    """Result of a transaction operation"""
    success: bool
    transaction: Optional[Transaction] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
