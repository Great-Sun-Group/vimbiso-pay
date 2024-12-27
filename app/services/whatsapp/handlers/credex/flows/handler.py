"""Core message handling for credex flows enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator
from .messages import (create_cancel_message, create_initial_prompt,
                       create_success_message)
from .steps import create_flow_steps

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


def validate_message(message: Dict[str, Any], step: Dict[str, Any]) -> bool:
    """Validate message for current step"""
    try:
        text = message.get("text", "").strip()
        if not text:
            return False
        return step["validator"](text) if step.get("validator") else True
    except Exception:
        return False


def handle_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle incoming message with strict state validation

    Args:
        state_manager: State manager instance
        message: Message to handle
        credex_service: CredEx service instance

    Returns:
        Dict[str, Any]: Response message
    """
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {
                "channel": state_manager.get("channel"),
                "member_id": state_manager.get("member_id"),
                "flow_data": state_manager.get("flow_data")
            },
            {"channel", "member_id", "flow_data"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info
        channel = state_manager.get("channel")
        flow_data = state_manager.get("flow_data")

        if not flow_data or "step" not in flow_data:
            return handle_initial_message(state_manager)
        return handle_flow_message(state_manager, message, credex_service)

    except ValueError as e:
        logger.error(f"Message handling error: {str(e)}")
        channel = state_manager.get("channel")
        return create_cancel_message(
            channel["identifier"] if channel else "unknown",
            str(e)
        )


def handle_initial_message(state_manager: Any) -> Dict[str, Any]:
    """Handle first message enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance

    Returns:
        Dict[str, Any]: Initial prompt message
    """
    try:
        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info
        channel = state_manager.get("channel")

        # Initialize flow data
        new_state = {
            "flow_data": {
                "id": "credex_flow",
                "step": 0
            }
        }

        # Update state
        state_manager.update(new_state)

        # Log success
        logger.info(f"Initialized credex flow for channel {channel['identifier']}")

        return create_initial_prompt(channel["identifier"])

    except ValueError as e:
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error logging: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Initial message error: {str(e)} for channel {channel_id}")
        return create_cancel_message(channel_id, str(e))


def handle_flow_message(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle message during flow enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        message: Message to handle
        credex_service: CredEx service instance

    Returns:
        Dict[str, Any]: Response message
    """
    try:
        # Validate input
        if not isinstance(message, dict):
            raise ValueError("Invalid message format")

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
        steps = create_flow_steps()
        current_step = steps[flow_data.get("step", 0)]

        # Validate input
        if not validate_message(message, current_step):
            raise ValueError(f"Invalid {current_step['id']} format")

        # Update flow data
        new_flow_data = flow_data.copy()
        new_flow_data.update({
            f"input_{flow_data['step']}": message.get("text", "").strip(),
            "step": flow_data["step"] + 1
        })

        # Update state
        state_manager.update({"flow_data": new_flow_data})

        # Log progress
        logger.info(f"Processed step {flow_data['step']} for channel {channel['identifier']}")

        # Get next step message or handle completion
        if flow_data["step"] + 1 < len(steps):
            return steps[flow_data["step"] + 1]["message"](state_manager)
        return handle_completion(state_manager, message, credex_service)

    except ValueError as e:
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error logging: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Flow message error: {str(e)} for channel {channel_id}")
        return create_cancel_message(channel_id, str(e))


def handle_completion(state_manager: Any, message: Dict[str, Any], credex_service: Any) -> Dict[str, Any]:
    """Handle flow completion enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        message: Message to handle
        credex_service: CredEx service instance

    Returns:
        Dict[str, Any]: Response message
    """
    try:
        # Validate input
        confirm = message.get("text", "").strip().lower()
        if confirm not in ["yes", "no"]:
            raise ValueError("Please reply with yes or no")

        # Validate state access at boundary
        validation = StateValidator.validate_before_access(
            {"channel": state_manager.get("channel")},
            {"channel"}
        )
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # Get channel info
        channel = state_manager.get("channel")

        if confirm == "yes":
            # Process the credex operation
            result = credex_service.process_flow(state_manager.get("flow_data"))
            if not result:
                raise ValueError("Operation failed")

            # Clear flow data
            state_manager.update({"flow_data": None})

            # Log success
            logger.info(f"Successfully completed credex flow for channel {channel['identifier']}")

            return create_success_message(channel["identifier"])

        # Clear flow data on cancel
        state_manager.update({"flow_data": None})

        # Log cancellation
        logger.info(f"Cancelled credex flow for channel {channel['identifier']}")

        return create_cancel_message(channel["identifier"])

    except ValueError as e:
        try:
            channel = state_manager.get("channel")
            channel_id = channel["identifier"] if channel else "unknown"
        except (ValueError, KeyError, TypeError) as err:
            logger.error(f"Failed to get channel for error logging: {str(err)}")
            channel_id = "unknown"

        logger.error(f"Completion error: {str(e)} for channel {channel_id}")
        return create_cancel_message(channel_id, str(e))
