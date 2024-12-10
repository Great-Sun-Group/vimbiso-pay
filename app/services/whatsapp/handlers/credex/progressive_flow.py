"""Progressive flow mixin for credex handlers"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.flow_handler import FlowHandler
from .offer_flow_v2 import CredexOfferFlow
from ...types import WhatsAppMessage

logger = logging.getLogger(__name__)


class ProgressiveFlowMixin:
    """Mixin for handling progressive flows"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize flow handler with service injector
        self.flow_handler = FlowHandler(self.service.state)
        self.flow_handler.register_flow(
            CredexOfferFlow,
            service_injector=self._inject_flow_services
        )
        logger.debug("Progressive flow initialized with service injector")

    def _inject_flow_services(self, flow: CredexOfferFlow) -> None:
        """Inject required services into flow"""
        flow.transaction_service = self.transaction_service
        flow.credex_service = self.service.credex_service
        logger.debug("Services injected into flow")

    def _handle_progressive_flow(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle progressive flow"""
        try:
            # Log message details
            logger.debug(f"Message type: {self.service.message_type}")
            logger.debug(f"Message body: {self.service.body}")
            if self.service.message_type == "interactive":
                interactive = self.service.message.get("interactive", {})
                logger.debug(f"Interactive type: {interactive.get('type')}")
                logger.debug(f"Interactive content: {interactive}")

            # Get member IDs and account info
            member_id = current_state["profile"]["data"]["action"]["details"]["memberID"]
            account_id = selected_profile["data"]["accountID"]
            account_name = selected_profile["data"].get("accountName", "Your Account")
            logger.debug(f"Member IDs: member={member_id}, account={account_id}")
            logger.debug(f"Account info: name={account_name}")

            # Check for offer actions first
            if self.service.message_type == "text" and isinstance(self.service.body, str):
                # Extract action and credex_id from command
                action_map = {
                    "accept_offer_": "accept",
                    "decline_offer_": "decline",
                    "cancel_offer_": "cancel"
                }

                for prefix, action in action_map.items():
                    if self.service.body.startswith(prefix):
                        credex_id = self.service.body.replace(prefix, "")
                        logger.debug(f"Handling offer action: {action} for credex_id: {credex_id}")

                        # Get active flow from state using CredexOfferFlow directly
                        flow = self.flow_handler.get_flow(
                            "credex_offer",
                            current_state.get("flow_data", {}).get("data", {})
                        )
                        if flow:
                            success, message = flow.handle_offer_action(action, credex_id)
                            if success:
                                # Clear flow state on success
                                current_state.pop("flow_data", None)
                                self.service.state.update_state(
                                    user_id=self.service.user.mobile_number,
                                    new_state=current_state,
                                    stage="menu",
                                    update_from="flow_complete"
                                )
                                # Return to menu with success message
                                menu_message = self.service.action_handler.auth_handler.handle_action_menu(
                                    message=f"✅ {message}\n\n",
                                    login=True  # Force fresh data
                                )
                                return True, WhatsAppMessage.from_core_message(menu_message)
                            else:
                                error_message = self._format_error_response(message)
                                return True, WhatsAppMessage.from_core_message(error_message)
                        break

            # Check if there's an active flow
            if "flow_data" in current_state:
                logger.debug("Found active flow, handling message")
                # Ensure member IDs and account info are in flow_data
                if "data" not in current_state["flow_data"]:
                    current_state["flow_data"]["data"] = {}
                current_state["flow_data"]["data"].update({
                    "authorizer_member_id": member_id,
                    "issuer_member_id": member_id,  # Set issuer_member_id to memberID
                    "sender_account": account_name,
                    "sender_account_id": account_id,
                    "phone": self.service.user.mobile_number
                })
                logger.debug(f"Updated flow_data: {current_state['flow_data']['data']}")

                # Update state before handling message
                self.service.state.update_state(
                    user_id=self.service.user.mobile_number,
                    new_state=current_state,
                    stage=current_state.get("stage", "credex"),
                    update_from="flow_update"
                )

                # Handle message with updated state
                message = self.flow_handler.handle_message(
                    self.service.user.mobile_number,
                    self.service.message
                )
                return True, WhatsAppMessage.from_core_message(message)

            # Start new flow if none active
            logger.debug("Starting new progressive flow")

            # Initialize flow_data with member IDs and account info
            current_state["flow_data"] = {
                "data": {
                    "authorizer_member_id": member_id,
                    "issuer_member_id": member_id,  # Set issuer_member_id to memberID
                    "sender_account": account_name,
                    "sender_account_id": account_id,
                    "phone": self.service.user.mobile_number
                }
            }
            logger.debug(f"Initial flow_data: {current_state['flow_data']['data']}")

            # Update state to ensure member IDs and account info are preserved
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=current_state,
                stage=current_state.get("stage", "credex"),
                update_from="flow_init"
            )

            result = self.flow_handler.start_flow(
                "credex_offer",
                self.service.user.mobile_number
            )

            # If result is a Flow instance
            if isinstance(result, CredexOfferFlow):
                # Set initial state
                result.state.update(current_state["flow_data"]["data"])
                logger.debug(f"Flow state after initialization: {result.state}")

                # Get message from current step
                message = result.current_step.message
                if callable(message):
                    message = message(result.state)
                return True, WhatsAppMessage.from_core_message(message)

            # If result is already a message or dict
            return True, WhatsAppMessage.from_core_message(result)

        except Exception as e:
            logger.exception(f"Error handling progressive flow: {str(e)}")
            error_message = self._format_error_response(str(e))
            return True, WhatsAppMessage.from_core_message(error_message)
