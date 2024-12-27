"""DEPRECATED: Use StateValidator and state_manager directly"""
import logging

logger = logging.getLogger(__name__)

# This module is deprecated.
# - Use StateValidator for state validation
# - Use state_manager.get() for state access
# - Use state_manager.update_state() for state updates
# - Store flow state in flow_data
# - Use WhatsAppMessage.create_text() directly
logger.warning("state_handler.py is deprecated")
