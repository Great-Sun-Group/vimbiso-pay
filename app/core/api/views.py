"""Cloud API webhook views"""
import logging
import sys
from datetime import datetime

from core.state.manager import StateManager
from core.messaging.types import ChannelIdentifier, ChannelType
from core.messaging.types import Message as DomainMessage
from core.messaging.types import MessageRecipient, TemplateContent
from decouple import config
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from core.messaging.service import MessagingService
from services.whatsapp.flow_processor import WhatsAppFlowProcessor
from services.whatsapp.service import WhatsAppMessagingService
from services.whatsapp.state_manager import StateManager as WhatsAppStateManager

# Configure logging with a standardized format
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {"asctime": "%(asctime)s", "levelname": "%(levelname)s", "name": "%(name)s", "message": "%(message)s", "taskName": null}',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def get_messaging_service(state_manager, channel_type: ChannelType):
    """Get properly initialized messaging service with state and channel

    Args:
        state_manager: State manager instance
        channel_type: Type of messaging channel (WhatsApp, SMS)

    Returns:
        MessagingService: Initialized messaging service
    """
    # Create channel-specific service based on type
    if channel_type == ChannelType.WHATSAPP:
        channel_service = WhatsAppMessagingService()
    elif channel_type == ChannelType.SMS:
        # TODO: Implement SMS service
        raise NotImplementedError("SMS channel not yet implemented")
    else:
        raise ValueError(f"Unsupported channel type: {channel_type}")

    # Create core messaging service with channel service and state
    messaging_service = MessagingService(
        channel_service=channel_service,
        state_manager=state_manager
    )

    return messaging_service


class CredexCloudApiWebhook(APIView):
    """Cloud Api Webhook"""

    permission_classes = []
    parser_classes = (JSONParser,)
    throttle_classes = []  # Disable throttling for webhook endpoint

    @staticmethod
    def post(request):
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Processing webhook request")

            # Validate basic webhook structure
            if not isinstance(request.data, dict):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            entries = request.data.get("entry", [])
            if not entries or not isinstance(entries, list):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            changes = entries[0].get("changes", [])
            if not changes or not isinstance(changes, list):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Check for mock testing mode
            is_mock_testing = request.headers.get('X-Mock-Testing') == 'true'

            # Get the raw payload and value
            value = changes[0].get("value", {})
            if not value or not isinstance(value, dict):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Identify channel type from value/headers and validate
            channel_type = None
            channel_id = None

            # Check for WhatsApp value
            if "messaging_product" in value and value["messaging_product"] == "whatsapp":
                channel_type = ChannelType.WHATSAPP

                # Validate WhatsApp value
                if not is_mock_testing:
                    metadata = value.get("metadata", {})
                    if not metadata or metadata.get("phone_number_id") != config("WHATSAPP_PHONE_NUMBER_ID"):
                        return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Handle WhatsApp status updates
                if value.get("statuses"):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Received status update")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Get WhatsApp contact info
                contacts = value.get("contacts", [])
                if not contacts or not isinstance(contacts, list):
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                contact = contacts[0]
                if not contact or not isinstance(contact, dict):
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                channel_id = contact.get("wa_id")
                if not channel_id:
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Check for SMS payload (stub for future implementation)
            elif "sms_provider" in value:
                channel_type = ChannelType.SMS
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Unknown channel type
            else:
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Validate we got the required information
            if not all([channel_type, channel_id]):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Initialize core state manager
            core_state_manager = StateManager(f"channel:{channel_id}")

            # Initialize channel-specific state manager
            if channel_type == ChannelType.WHATSAPP:
                state_manager = WhatsAppStateManager(core_state_manager)
            else:
                state_manager = core_state_manager

            # Store state
            state_manager.update_state({
                "channel": {
                    "type": channel_type.value,
                    "identifier": channel_id
                },
                "mock_testing": is_mock_testing,
                "_metadata": {
                    "updated_at": datetime.utcnow().isoformat()
                }
            })

            try:
                # Get messaging service for channel
                service = get_messaging_service(state_manager, channel_type)

                # Create flow processor for channel type
                if channel_type == ChannelType.WHATSAPP:
                    flow_processor = WhatsAppFlowProcessor(service, state_manager)
                else:
                    raise ValueError(f"Unsupported channel type: {channel_type}")

                # Process message - component handles its own messaging
                flow_processor.process_message(request.data)
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Message processing error: {str(e)}")
                return JsonResponse(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return JsonResponse(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, *args, **kwargs):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Webhook verification request")
        return HttpResponse(request.query_params.get("hub.challenge"), 200)


class WipeCache(APIView):
    """Message"""

    parser_classes = (JSONParser,)

    @staticmethod
    def post(request):
        number = request.data.get("number")
        if number:
            cache.delete(number)
        return JsonResponse({"message": "Success"}, status=status.HTTP_200_OK)


class CredexSendMessageWebhook(APIView):
    """Channel-agnostic message sending webhook"""

    parser_classes = (JSONParser,)
    throttle_classes = []  # Disable throttling for webhook endpoint

    @staticmethod
    def post(request):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Processing send message request")

        # Validate API key
        if request.headers.get("apiKey", "").lower() != config("CLIENT_API_KEY").lower():
            return JsonResponse(
                {"status": "error", "message": "Invalid API key"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate required fields
        required_fields = ["phoneNumber", "memberName", "message", "channel"]
        if not all(field in request.data for field in required_fields):
            return JsonResponse(
                {"status": "error", "message": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get channel type
            channel = request.data["channel"].upper()
            try:
                channel_type = ChannelType[channel]
            except KeyError:
                return JsonResponse(
                    {"status": "error", "message": f"Unsupported channel: {channel}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create channel-agnostic message
            recipient = MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=channel_type,
                    value=request.data["phoneNumber"]
                )
            )

            # Create template message
            message = DomainMessage(
                recipient=recipient,
                content=TemplateContent(
                    name="incoming_notification",
                    language={"code": "en_US"},
                    components=[{
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": request.data["memberName"]
                            },
                            {
                                "type": "text",
                                "text": request.data["message"]
                            }
                        ]
                    }]
                )
            )

            # Initialize core state manager
            core_state_manager = StateManager(f"channel:{request.data['phoneNumber']}")

            # Initialize channel-specific state manager
            if channel_type == ChannelType.WHATSAPP:
                state_manager = WhatsAppStateManager(core_state_manager)
            else:
                state_manager = core_state_manager

            # Get messaging service for channel
            service = get_messaging_service(state_manager, channel_type)

            # Send through service
            response = service.send_message(message)
            return JsonResponse(response.to_dict(), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Message sending error: {str(e)}")
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
