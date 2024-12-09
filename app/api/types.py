"""
Type definitions for webhook handling.
Defines data structures and types used in webhook processing.
"""
from typing import TypedDict, Optional, List, Union
from datetime import datetime


class WebhookMetadata(TypedDict):
    """Metadata included with all webhooks."""
    webhook_id: str
    timestamp: datetime
    signature: str
    event_type: str


class CompanyUpdatePayload(TypedDict):
    """Payload structure for company update webhooks."""
    company_id: str
    name: str
    status: str
    updated_fields: List[str]
    metadata: Optional[dict]


class MemberUpdatePayload(TypedDict):
    """Payload structure for member update webhooks."""
    member_id: str
    company_id: str
    status: str
    updated_fields: List[str]
    metadata: Optional[dict]


class OfferUpdatePayload(TypedDict):
    """Payload structure for offer update webhooks."""
    offer_id: str
    company_id: str
    status: str
    amount: float
    currency: str
    expiry: datetime
    metadata: Optional[dict]


WebhookPayload = Union[CompanyUpdatePayload, MemberUpdatePayload, OfferUpdatePayload]


class WebhookRequest(TypedDict):
    """Complete webhook request structure."""
    metadata: WebhookMetadata
    payload: WebhookPayload
