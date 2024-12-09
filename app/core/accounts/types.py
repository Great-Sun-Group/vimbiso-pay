from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AccountType(Enum):
    """Types of accounts that can exist"""
    PERSONAL = "personal"
    BUSINESS = "business"
    ORGANIZATION = "organization"


class AccountStatus(Enum):
    """Possible states of an account"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CLOSED = "closed"


class AccountRole(Enum):
    """Roles a member can have in an account"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


@dataclass
class AccountMember:
    """Member information within an account"""
    member_id: str
    role: AccountRole
    name: str
    handle: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    joined_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountSettings:
    """Account configuration settings"""
    default_denomination: str
    allow_unsecured_credex: bool = False
    require_2fa: bool = False
    auto_approve_members: bool = False
    notification_preferences: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Account:
    """Core account information"""
    id: str
    name: str
    type: AccountType
    status: AccountStatus
    owner_id: str
    settings: AccountSettings
    members: List[AccountMember]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountInvite:
    """Account membership invitation"""
    id: str
    account_id: str
    inviter_id: str
    invitee_handle: str
    role: AccountRole
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountUpdateResult:
    """Result of an account update operation"""
    success: bool
    account: Optional[Account] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountMemberResult:
    """Result of an account member operation"""
    success: bool
    member: Optional[AccountMember] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountInviteResult:
    """Result of an account invite operation"""
    success: bool
    invite: Optional[AccountInvite] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
