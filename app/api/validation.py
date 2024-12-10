"""
Validation utilities for webhook requests.
Implements validation logic for different webhook types.
"""
from datetime import datetime
from typing import Any, Dict, Tuple


class WebhookValidator:
    """Validator for webhook requests."""

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate webhook metadata."""
        required_fields = {'webhook_id', 'timestamp', 'signature', 'event_type'}

        if not all(field in metadata for field in required_fields):
            missing = required_fields - set(metadata.keys())
            return False, f"Missing required metadata fields: {missing}"

        try:
            # Validate timestamp format
            if isinstance(metadata['timestamp'], str):
                datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))
            elif not isinstance(metadata['timestamp'], datetime):
                return False, "Invalid timestamp format"
        except ValueError:
            return False, "Invalid timestamp format"

        return True, ""

    @staticmethod
    def validate_company_update(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate company update payload."""
        required_fields = {'company_id', 'name', 'status', 'updated_fields'}

        if not all(field in payload for field in required_fields):
            missing = required_fields - set(payload.keys())
            return False, f"Missing required company fields: {missing}"

        if not isinstance(payload['updated_fields'], list):
            return False, "updated_fields must be a list"

        return True, ""

    @staticmethod
    def validate_member_update(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate member update payload."""
        required_fields = {'member_id', 'company_id', 'status', 'updated_fields'}

        if not all(field in payload for field in required_fields):
            missing = required_fields - set(payload.keys())
            return False, f"Missing required member fields: {missing}"

        if not isinstance(payload['updated_fields'], list):
            return False, "updated_fields must be a list"

        return True, ""

    @staticmethod
    def validate_offer_update(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate offer update payload."""
        required_fields = {'offer_id', 'company_id', 'status', 'amount', 'denomination', 'expiry'}

        if not all(field in payload for field in required_fields):
            missing = required_fields - set(payload.keys())
            return False, f"Missing required offer fields: {missing}"

        try:
            float(payload['amount'])
        except (TypeError, ValueError):
            return False, "Invalid amount format"

        try:
            if isinstance(payload['expiry'], str):
                datetime.fromisoformat(payload['expiry'].replace('Z', '+00:00'))
            elif not isinstance(payload['expiry'], datetime):
                return False, "Invalid expiry format"
        except ValueError:
            return False, "Invalid expiry format"

        return True, ""

    def validate_webhook(self, webhook: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate complete webhook request."""
        if not all(key in webhook for key in ('metadata', 'payload')):
            return False, "Missing required webhook sections"

        # Validate metadata
        valid_metadata, metadata_error = self.validate_metadata(webhook['metadata'])
        if not valid_metadata:
            return False, metadata_error

        # Get event type and validate corresponding payload
        event_type = webhook['metadata']['event_type']
        validators = {
            'company_update': self.validate_company_update,
            'member_update': self.validate_member_update,
            'offer_update': self.validate_offer_update
        }

        validator = validators.get(event_type)
        if not validator:
            return False, f"Unsupported event type: {event_type}"

        valid_payload, payload_error = validator(webhook['payload'])
        if not valid_payload:
            return False, payload_error

        return True, ""
