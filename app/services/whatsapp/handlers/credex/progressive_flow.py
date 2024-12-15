"""Progressive flow mixin for credex handlers"""
import logging
from typing import Any, Dict, Tuple

from core.messaging.flow_handler import FlowHandler
from .offer_flow_v2 import CredexOfferFlow
from .action_flows import AcceptCredexFlow, DeclineCredexFlow, CancelCredexFlow
from ...types import WhatsAppMessage
from services.state.service import StateStage

logger = logging.getLogger(__name__)


class ProgressiveFlowMixin:
    """Mixin for handling progressive flows"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flow_handler = FlowHandler(self.service.state)
        self._register_flows()

    def _register_flows(self):
        """Register all flows with service injector"""
        flows = [
            CredexOfferFlow,
            AcceptCredexFlow,
            DeclineCredexFlow,
            CancelCredexFlow
        ]
        for flow_class in flows:
            self.flow_handler.register_flow(
                flow_class,
                service_injector=self._inject_flow_services
            )
        logger.debug("Progressive flows registered with service injector")

    def _inject_flow_services(self, flow: Any) -> None:
        """Inject required services into flow"""
        flow.transaction_service = self.transaction_service
        flow.credex_service = self.service.credex_service
        flow.state_service = self.service.state
        logger.debug(f"Services injected into flow: {type(flow).__name__}")

    def _initialize_flow_state(
            self, current_state: Dict[str, Any], member_id: str,
            sender_account_id: str, sender_account_name: str) -> Dict[str, Any]:
        """Initialize flow state with required fields"""
        return {
            "id": "credex_offer",
            "stage": StateStage.CREDEX.value,
            "option": "handle_action_offer_credex",
            "data": {
                "profile": current_state["profile"]["data"],
                "current_account": current_state.get("current_account"),
                "authorizer_member_id": member_id,
                "issuer_member_id": member_id,
                "sender_account": sender_account_name,
                "sender_account_id": sender_account_id,
                "phone": self.service.user.mobile_number
            }
        }

    def _validate_profile_data(self, profile_data: Dict[str, Any]) -> bool:
        """Validate profile data structure"""
        try:
            if not isinstance(profile_data, dict):
                logger.error("Profile data is not a dictionary")
                return False

            if "data" not in profile_data:
                logger.error("Profile data missing 'data' key")
                return False

            if "action" not in profile_data["data"]:
                logger.error("Profile data missing 'action' key")
                return False

            if "details" not in profile_data["data"]["action"]:
                logger.error("Profile data missing 'details' key")
                return False

            if "memberID" not in profile_data["data"]["action"]["details"]:
                logger.error("Profile data missing 'memberID' key")
                return False

            return True
        except Exception as e:
            logger.error(f"Profile validation error: {str(e)}")
            return False

    def _extract_sender_account_info(self, profile_data: Dict[str, Any], selected_profile: Dict[str, Any]) -> Tuple[str, str]:
        """Extract sender account info from profile data"""
        try:
            if selected_profile and isinstance(selected_profile, dict):
                account_data = selected_profile.get("data", {})
                if account_data.get("isOwnedAccount"):
                    return account_data.get("accountID"), account_data.get("accountName", "Your Account")

            dashboard = profile_data.get("dashboard", {})
            accounts = dashboard.get("accounts", [])
            for account in accounts:
                if (account.get("success") and
                        account["data"].get("accountHandle") == self.service.user.mobile_number):
                    account_data = account["data"]
                    return account_data.get("accountID"), account_data.get("accountName", "Your Account")

            return None, "Your Account"
        except Exception as e:
            logger.error(f"Error extracting sender account info: {str(e)}")
            return None, "Your Account"

    def _update_flow_state(
        self,
        current_state: Dict[str, Any],
        stage: str,
        update_from: str,
        option: str = None,
        preserve_flow: bool = True
    ) -> bool:
        """Update state with consistent pattern"""
        try:
            if not isinstance(current_state, dict):
                logger.error("Invalid current state type")
                return False

            # Validate profile data
            profile_data = current_state.get("profile", {})
            if not self._validate_profile_data(profile_data):
                logger.error("Invalid profile data structure")
                return False

            # Get member ID and account info
            member_id = profile_data["data"]["action"]["details"]["memberID"]
            selected_profile = current_state.get("current_account")
            sender_account_id, sender_account_name = self._extract_sender_account_info(
                profile_data, selected_profile
            )

            # Create new state with required fields
            new_state = {
                "profile": profile_data,
                "current_account": selected_profile,
                "stage": stage,
                "option": option or "handle_action_offer_credex",
                "authorizer_member_id": member_id,
                "issuer_member_id": member_id,
                "sender_account": sender_account_name,
                "sender_account_id": sender_account_id,
                "phone": self.service.user.mobile_number,
                "last_refresh": True
            }

            # Preserve JWT token
            if self.service.credex_service and self.service.credex_service.jwt_token:
                new_state["jwt_token"] = self.service.credex_service.jwt_token

            # Preserve or initialize flow data
            if preserve_flow and "flow_data" in current_state:
                flow_data = current_state["flow_data"]
                flow_data["stage"] = stage
                flow_data["option"] = option or "handle_action_offer_credex"
                new_state["flow_data"] = flow_data
            elif preserve_flow:
                new_state["flow_data"] = self._initialize_flow_state(
                    current_state, member_id, sender_account_id, sender_account_name
                )

            # Update state
            self.service.state.update_state(
                user_id=self.service.user.mobile_number,
                new_state=new_state,
                stage=stage,
                update_from=update_from,
                option=option
            )
            logger.debug(f"Flow state updated from {update_from}")
            logger.debug(f"Updated state: {new_state}")
            return True

        except Exception as e:
            logger.error(f"Error updating flow state: {str(e)}")
            return False

    def _handle_progressive_flow(
        self,
        current_state: Dict[str, Any],
        selected_profile: Dict[str, Any]
    ) -> Tuple[bool, WhatsAppMessage]:
        """Handle progressive flow"""
        try:
            # Validate current state
            if not isinstance(current_state, dict):
                raise ValueError("Invalid current state type")

            # Validate profile data
            if not self._validate_profile_data(current_state.get("profile", {})):
                raise ValueError("Invalid profile data structure")

            # Log message details
            logger.debug(f"Message type: {self.service.message_type}")
            logger.debug(f"Message body: {self.service.body}")

            # Get member ID and account info
            member_id = current_state["profile"]["data"]["action"]["details"]["memberID"]
            sender_account_id, sender_account_name = self._extract_sender_account_info(
                current_state["profile"]["data"],
                selected_profile
            )

            # Initialize base state
            current_state.update({
                "stage": StateStage.CREDEX.value,
                "option": "handle_action_offer_credex",
                "authorizer_member_id": member_id,
                "issuer_member_id": member_id,
                "sender_account": sender_account_name,
                "sender_account_id": sender_account_id,
                "phone": self.service.user.mobile_number,
                "current_account": selected_profile
            })

            # Handle menu action selection
            if (self.service.message_type == "interactive" and
                    self.service.message.get("interactive", {}).get("type") == "list_reply"):
                selected_id = self.service.message["interactive"]["list_reply"].get("id")
                if selected_id == "handle_action_offer_credex":
                    logger.debug("Starting new credex offer flow")
                    # Initialize flow data
                    current_state["flow_data"] = self._initialize_flow_state(
                        current_state, member_id, sender_account_id, sender_account_name
                    )

                    # Update state
                    if not self._update_flow_state(
                        current_state=current_state,
                        stage=StateStage.CREDEX.value,
                        update_from="flow_init",
                        option="handle_action_offer_credex"
                    ):
                        raise ValueError("Failed to update flow state")

                    # Start flow
                    result = self.flow_handler.start_flow(
                        "credex_offer",
                        self.service.user.mobile_number
                    )

                    if isinstance(result, CredexOfferFlow):
                        result.initialize_from_profile(current_state["profile"]["data"])
                        result.state.update(current_state["flow_data"]["data"])
                        message = result.current_step.message
                        if callable(message):
                            message = message(result.state)
                        return True, WhatsAppMessage.from_core_message(message)
                    return True, WhatsAppMessage.from_core_message(result)

            # Check for offer actions
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
                                # Update state without flow data
                                self._update_flow_state(
                                    current_state=current_state,
                                    stage=StateStage.MENU.value,
                                    update_from=f"credex_{action}_complete",
                                    option="handle_action_menu",
                                    preserve_flow=False
                                )
                                # Return to menu with success message
                                menu_message = self.service.action_handler.auth_handler.handle_action_menu(
                                    message=f"✅ {message}\n\n",
                                    login=False  # Don't need API call since we have fresh data
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
                    "profile": current_state["profile"]["data"],
                    "current_account": selected_profile,  # Include selected account
                    "authorizer_member_id": member_id,
                    "issuer_member_id": member_id,
                    "sender_account": sender_account_name,
                    "sender_account_id": sender_account_id,
                    "phone": self.service.user.mobile_number
                })
                logger.debug(f"Updated flow_data: {current_state['flow_data']['data']}")

                # Update state before handling message
                self._update_flow_state(
                    current_state=current_state,
                    stage=StateStage.CREDEX.value,  # Force credex stage
                    update_from="flow_update"
                )

                # Handle message with updated state
                message = self.flow_handler.handle_message(
                    self.service.user.mobile_number,
                    self.service.message
                )

                # Get fresh state after message handling
                current_state = self.service.state.get_state(self.service.user.mobile_number)
                # Re-ensure member IDs and account info are present
                current_state.update({
                    "authorizer_member_id": member_id,
                    "issuer_member_id": member_id,
                    "sender_account": sender_account_name,
                    "sender_account_id": sender_account_id,
                    "phone": self.service.user.mobile_number,
                    "current_account": selected_profile  # Preserve selected account
                })
                if "flow_data" in current_state and "data" in current_state["flow_data"]:
                    current_state["flow_data"]["data"].update({
                        "profile": current_state["profile"]["data"],
                        "current_account": selected_profile,  # Include selected account
                        "authorizer_member_id": member_id,
                        "issuer_member_id": member_id,
                        "sender_account": sender_account_name,
                        "sender_account_id": sender_account_id,
                        "phone": self.service.user.mobile_number
                    })

                if message is None:
                    # Flow completed successfully
                    logger.debug("Flow completed successfully")
                    # Update state without flow data
                    self._update_flow_state(
                        current_state=current_state,
                        stage=StateStage.MENU.value,
                        update_from="flow_complete",
                        option="handle_action_menu",
                        preserve_flow=False
                    )
                    # Return to menu with success message
                    menu_message = self.service.action_handler.auth_handler.handle_action_menu(
                        message="✅ Credex offer created successfully!\n\n",
                        login=False  # Don't need API call since we have fresh data
                    )
                    return True, WhatsAppMessage.from_core_message(menu_message)
                return True, WhatsAppMessage.from_core_message(message)

            # Start new flow if none active
            logger.debug("Starting new progressive flow")

            # Initialize flow_data with member IDs and account info
            current_state["flow_data"] = {
                "id": "credex_offer",  # Set correct flow ID
                "data": {
                    "profile": current_state["profile"]["data"],
                    "current_account": selected_profile,  # Include selected account
                    "authorizer_member_id": member_id,
                    "issuer_member_id": member_id,
                    "sender_account": sender_account_name,
                    "sender_account_id": sender_account_id,
                    "phone": self.service.user.mobile_number
                }
            }
            logger.debug(f"Initial flow_data: {current_state['flow_data']['data']}")

            # Update state with new flow
            self._update_flow_state(
                current_state=current_state,
                stage=StateStage.CREDEX.value,  # Force credex stage
                update_from="flow_init"
            )

            result = self.flow_handler.start_flow(
                "credex_offer",
                self.service.user.mobile_number
            )

            # If result is a Flow instance
            if isinstance(result, CredexOfferFlow):
                # Initialize flow with profile data
                result.initialize_from_profile(current_state["profile"]["data"])
                # Set initial state with all required data
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
