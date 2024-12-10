"""Progressive flow mixin for credex handlers"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.flow_handler import FlowHandler
from .offer_flow_v2 import CredexOfferFlow
from ...types import WhatsAppMessage
from core.config.constants import USE_PROGRESSIVE_FLOW

logger = logging.getLogger(__name__)


class ProgressiveFlowMixin:
    """Mixin for handling progressive flows"""

    def __init__(self, *args, **kwargs):
        # Remove use_progressive_flow from kwargs before passing to super
        use_progressive_flow = kwargs.pop('use_progressive_flow', USE_PROGRESSIVE_FLOW)
        super().__init__(*args, **kwargs)

        # Initialize flow handler
        self.flow_handler = FlowHandler(self.service.state)
        self.flow_handler.register_flow(CredexOfferFlow)
        self.use_progressive_flow = use_progressive_flow
        logger.debug(f"Progressive flow initialized with use_progressive_flow={self.use_progressive_flow}")

    def _handle_progressive_flow(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> Tuple[bool, WhatsAppMessage]:
        """Handle progressive flow if active"""
        try:
            # Check if we should use progressive flow
            logger.debug(f"Checking progressive flow with use_progressive_flow={self.use_progressive_flow}")
            if not self.use_progressive_flow:
                logger.debug("Progressive flow disabled, falling back to old flow")
                return False, None

            # Log message details
            logger.debug(f"Message type: {self.service.message_type}")
            logger.debug(f"Message body: {self.service.body}")
            if self.service.message_type == "interactive":
                interactive = self.service.message.get("interactive", {})
                logger.debug(f"Interactive type: {interactive.get('type')}")
                logger.debug(f"Interactive content: {interactive}")

            # Check if there's an active flow
            if "flow_data" in current_state:
                logger.debug("Found active flow, handling message")
                return True, self.flow_handler.handle_message(
                    self.service.user.mobile_number,
                    self.service.message
                )

            # Check if we're starting a new offer flow
            # Handle both direct command and interactive message
            is_offer_command = (
                current_state.get("stage") == "credex" and
                current_state.get("option") == "handle_action_offer_credex" and
                not current_state.get("offer_flow")
            )

            if is_offer_command:
                logger.debug("Starting new progressive flow")
                # Start new flow
                flow = self.flow_handler.start_flow(
                    "credex_offer",
                    self.service.user.mobile_number
                )
                if isinstance(flow, CredexOfferFlow):
                    # Inject required services
                    flow.transaction_service = self.transaction_service
                    # Set initial state
                    flow.state.update({
                        "authorizer_member_id": current_state["profile"]["data"]["action"]["details"]["memberID"],
                        "issuer_member_id": selected_profile["data"]["accountID"],
                    })
                    logger.debug("Flow initialized with transaction service and initial state")
                return True, flow.current_step.message

            logger.debug("No flow conditions met, returning False")
            return False, None

        except Exception as e:
            logger.exception(f"Error handling progressive flow: {str(e)}")
            return True, self._format_error_response(str(e))
