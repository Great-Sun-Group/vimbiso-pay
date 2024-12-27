"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.types import (
    ChannelIdentifier,
    ChannelType,
    Message,
    MessageRecipient,
    TextContent
)
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

REQUIRED_FIELDS = {"channel", "member_id", "account_id", "authenticated", "jwt_token"}


def get_amount_prompt(state_manager: Any) -> Message:
    """Get amount prompt with strict state validation"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                member_id=state_manager.get("member_id"),
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Enter amount to offer (e.g. 100 USD):"
            )
        )
    except ValueError as e:
        return Message(
            recipient=MessageRecipient(
                member_id="unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body=f"Error: {str(e)}"
            )
        )


def validate_amount(amount: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Validate amount input"""
    try:
        if not amount or len(amount.split()) != 2:
            return False, "Invalid amount format. Please enter amount and currency (e.g. 100 USD)", None

        value, denomination = amount.split()
        try:
            value = float(value)
            if value <= 0:
                return False, "Amount must be greater than 0", None
        except ValueError:
            return False, "Invalid amount value", None

        if denomination not in {"USD", "EUR", "GBP"}:
            return False, "Invalid currency. Supported: USD, EUR, GBP", None

        return True, None, {"amount": value, "denomination": denomination}
    except Exception as e:
        return False, str(e), None


def store_amount(state_manager: Any, amount: str) -> Tuple[bool, Optional[str]]:
    """Store validated amount in state"""
    try:
        # Get flow data (SINGLE SOURCE OF TRUTH)
        flow_data = state_manager.get("flow_data")
        if not isinstance(flow_data, dict):
            flow_data = {}

        # Validate amount
        valid, error, amount_data = validate_amount(amount)
        if not valid:
            return False, error

        # Update state (validation handled by state manager)
        new_flow_data = {
            **flow_data,
            "amount": amount_data["amount"],
            "denomination": amount_data["denomination"],
            "current_step": "handle"
        }

        success, error = state_manager.update_state({"flow_data": new_flow_data})
        if not success:
            return False, error

        # Log success
        channel = state_manager.get("channel")
        logger.info(
            f"Stored amount {amount_data['amount']} {amount_data['denomination']} "
            f"for channel {channel['identifier']}"
        )
        return True, None

    except Exception as e:
        logger.error(f"Failed to store amount: {str(e)}")
        return False, str(e)


def get_handle_prompt(state_manager: Any) -> Message:
    """Get handle prompt with strict state validation"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                member_id=state_manager.get("member_id"),
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Enter recipient handle:"
            )
        )
    except ValueError as e:
        return Message(
            recipient=MessageRecipient(
                member_id="unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body=f"Error: {str(e)}"
            )
        )


def validate_handle(handle: str) -> Tuple[bool, Optional[str]]:
    """Validate handle input"""
    if not handle or len(handle) < 3:
        return False, "Handle must be at least 3 characters"
    return True, None


def store_handle(state_manager: Any, handle: str) -> Tuple[bool, Optional[str]]:
    """Store validated handle in state"""
    try:
        # Get flow data (SINGLE SOURCE OF TRUTH)
        flow_data = state_manager.get("flow_data")
        if not isinstance(flow_data, dict):
            flow_data = {}

        # Validate handle
        valid, error = validate_handle(handle)
        if not valid:
            return False, error

        # Update state (validation handled by state manager)
        new_flow_data = {
            **flow_data,
            "handle": handle.strip(),
            "current_step": "confirm"
        }

        success, error = state_manager.update_state({"flow_data": new_flow_data})
        if not success:
            return False, error

        # Log success
        channel = state_manager.get("channel")
        logger.info(f"Stored handle {handle} for channel {channel['identifier']}")
        return True, None

    except Exception as e:
        logger.error(f"Failed to store handle: {str(e)}")
        return False, str(e)


def create_offer_confirmation_with_state(state_manager: Any) -> Message:
    """Create offer confirmation message with state data"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "flow_data": state_manager.get("flow_data")
            },
            {"channel", "flow_data"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get required data
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        # Format confirmation message
        confirmation_text = (
            f"Please confirm offer details:\n\n"
            f"Amount: {flow_data['amount']} {flow_data['denomination']}\n"
            f"Recipient: {flow_data['handle']}\n\n"
            f"Reply 'yes' to confirm or 'no' to cancel"
        )

        return Message(
            recipient=MessageRecipient(
                member_id=state_manager.get("member_id"),
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body=confirmation_text
            )
        )

    except ValueError as e:
        return Message(
            recipient=MessageRecipient(
                member_id="unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body=f"Error: {str(e)}"
            )
        )


def get_confirmation_message(state_manager: Any) -> Message:
    """Get confirmation message with strict state validation"""
    try:
        # Get required data (validation handled by flow steps)
        flow_data = state_manager.get("flow_data")
        if not flow_data:
            raise ValueError("Missing flow data")

        return create_offer_confirmation_with_state(state_manager)

    except ValueError as e:
        return Message(
            recipient=MessageRecipient(
                member_id="unknown",
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value="unknown"
                )
            ),
            content=TextContent(
                body=f"Error: {str(e)}"
            )
        )


def complete_offer(state_manager: Any, credex_service: Any) -> Tuple[bool, Dict[str, Any]]:
    """Complete offer flow enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Get required data (already validated)
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        # Make API call
        offer_data = {
            "amount": flow_data["amount"],
            "denomination": flow_data["denomination"],
            "handle": flow_data["handle"]
        }
        success, response = credex_service['offer_credex'](offer_data)
        if not success:
            error_msg = response.get("message", "Failed to create offer")
            logger.error(f"API call failed: {error_msg}")
            return False, {"message": error_msg}

        # Log success
        audit.log_flow_event(
            "offer_flow",
            "completion_success",
            None,
            {
                "channel_id": channel["identifier"],
                "amount": flow_data["amount"],
                "denomination": flow_data["denomination"],
                "handle": flow_data["handle"]
            },
            "success"
        )

        return True, response

    except Exception as e:
        logger.error(f"Offer completion failed: {str(e)}")
        return False, {"message": str(e)}


def process_offer_step(
    state_manager: Any,
    step: str,
    input_data: Any = None,
    credex_service: Any = None
) -> Message:
    """Process offer step enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {field: state_manager.get(field) for field in REQUIRED_FIELDS},
            REQUIRED_FIELDS
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Handle each step
        if step == "amount":
            if input_data:
                success, error = store_amount(state_manager, input_data)
                if not success:
                    raise ValueError(error)
                return get_handle_prompt(state_manager)
            return get_amount_prompt(state_manager)

        elif step == "handle":
            if input_data:
                success, error = store_handle(state_manager, input_data)
                if not success:
                    raise ValueError(error)
                return get_confirmation_message(state_manager)
            return get_handle_prompt(state_manager)

        elif step == "confirm":
            if not credex_service:
                raise ValueError("CredEx service required for confirmation")

            if input_data and input_data.lower() == "yes":
                success, response = complete_offer(state_manager, credex_service)
                if not success:
                    raise ValueError(response["message"])
                return Message(
                    recipient=MessageRecipient(
                        member_id=state_manager.get("member_id"),
                        channel_id=ChannelIdentifier(
                            channel=ChannelType.WHATSAPP,
                            value=state_manager.get("channel")["identifier"]
                        )
                    ),
                    content=TextContent(
                        body="✅ Offer created successfully!"
                    )
                )
            return get_confirmation_message(state_manager)

        else:
            raise ValueError(f"Invalid offer step: {step}")

    except ValueError as e:
        return Message(
            recipient=MessageRecipient(
                member_id=state_manager.get("member_id", "unknown"),
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=state_manager.get("channel", {}).get("identifier", "unknown")
                )
            ),
            content=TextContent(
                body=f"Error: {str(e)}"
            )
        )
