"""Webhook validation utilities"""
from datetime import datetime
from typing import Any, Dict

from core.utils.error_handler import ErrorHandler


def validate_webhook(webhook: Dict[str, Any]) -> Dict:
    """Validate complete webhook request"""
    # Check required sections
    if not all(key in webhook for key in ('metadata', 'payload')):
        return ErrorHandler.handle_system_error(
            code="MISSING_SECTIONS",
            service="webhook",
            action="validate",
            message="Missing required webhook sections"
        )

    # Validate metadata
    metadata_error = validate_metadata(webhook['metadata'])
    if metadata_error:
        return metadata_error

    # Validate payload by type
    event_type = webhook['metadata']['event_type']
    validators = {
        'company_update': validate_company_update,
        'member_update': validate_member_update,
        'offer_update': validate_offer_update
    }

    validator = validators.get(event_type)
    if not validator:
        return ErrorHandler.handle_system_error(
            code="INVALID_TYPE",
            service="webhook",
            action="validate",
            message=f"Unsupported event type: {event_type}"
        )

    return validator(webhook['payload'])


def validate_metadata(metadata: Dict[str, Any]) -> Dict:
    """Validate webhook metadata"""
    required_fields = {'webhook_id', 'timestamp', 'signature', 'event_type'}

    # Check required fields
    if not all(field in metadata for field in required_fields):
        missing = required_fields - set(metadata.keys())
        return ErrorHandler.handle_system_error(
            code="MISSING_METADATA",
            service="webhook",
            action="validate_metadata",
            message=f"Missing required metadata fields: {missing}"
        )

    # Validate timestamp
    try:
        if isinstance(metadata['timestamp'], str):
            datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))
        elif not isinstance(metadata['timestamp'], datetime):
            raise ValueError("Invalid timestamp type")
    except ValueError:
        return ErrorHandler.handle_system_error(
            code="INVALID_TIMESTAMP",
            service="webhook",
            action="validate_metadata",
            message="Invalid timestamp format"
        )

    return {}


def validate_company_update(payload: Dict[str, Any]) -> Dict:
    """Validate company update payload"""
    required_fields = {'company_id', 'name', 'status', 'updated_fields'}

    # Check required fields
    if not all(field in payload for field in required_fields):
        missing = required_fields - set(payload.keys())
        return ErrorHandler.handle_system_error(
            code="MISSING_FIELDS",
            service="webhook",
            action="validate_company",
            message=f"Missing required company fields: {missing}"
        )

    # Validate updated_fields
    if not isinstance(payload['updated_fields'], list):
        return ErrorHandler.handle_system_error(
            code="INVALID_FIELD",
            service="webhook",
            action="validate_company",
            message="updated_fields must be a list"
        )

    return {}


def validate_member_update(payload: Dict[str, Any]) -> Dict:
    """Validate member update payload"""
    required_fields = {'member_id', 'company_id', 'status', 'updated_fields'}

    # Check required fields
    if not all(field in payload for field in required_fields):
        missing = required_fields - set(payload.keys())
        return ErrorHandler.handle_system_error(
            code="MISSING_FIELDS",
            service="webhook",
            action="validate_member",
            message=f"Missing required member fields: {missing}"
        )

    # Validate updated_fields
    if not isinstance(payload['updated_fields'], list):
        return ErrorHandler.handle_system_error(
            code="INVALID_FIELD",
            service="webhook",
            action="validate_member",
            message="updated_fields must be a list"
        )

    return {}


def validate_offer_update(payload: Dict[str, Any]) -> Dict:
    """Validate offer update payload"""
    required_fields = {'offer_id', 'company_id', 'status', 'amount', 'denomination', 'expiry'}

    # Check required fields
    if not all(field in payload for field in required_fields):
        missing = required_fields - set(payload.keys())
        return ErrorHandler.handle_system_error(
            code="MISSING_FIELDS",
            service="webhook",
            action="validate_offer",
            message=f"Missing required offer fields: {missing}"
        )

    # Validate amount
    try:
        float(payload['amount'])
    except (TypeError, ValueError):
        return ErrorHandler.handle_system_error(
            code="INVALID_AMOUNT",
            service="webhook",
            action="validate_offer",
            message="Invalid amount format"
        )

    # Validate expiry
    try:
        if isinstance(payload['expiry'], str):
            datetime.fromisoformat(payload['expiry'].replace('Z', '+00:00'))
        elif not isinstance(payload['expiry'], datetime):
            raise ValueError("Invalid expiry type")
    except ValueError:
        return ErrorHandler.handle_system_error(
            code="INVALID_EXPIRY",
            service="webhook",
            action="validate_offer",
            message="Invalid expiry format"
        )

    return {}
