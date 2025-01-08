"""Cloud API webhook views"""
import logging
import sys
from datetime import datetime

from core.config.state_manager import StateManager
from core.messaging.types import ChannelIdentifier, ChannelType
from core.messaging.types import Message as DomainMessage
from core.messaging.types import MessageRecipient, TemplateContent
from decouple import config
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from services.messaging.service import MessagingService
from services.whatsapp.flow_processor import WhatsAppFlowProcessor
from services.whatsapp.service import WhatsAppMessagingService

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
            logger.info("Received webhook request")

            # Validate basic webhook structure
            if not isinstance(request.data, dict):
                logger.warning("Invalid request data format")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            entries = request.data.get("entry", [])
            if not entries or not isinstance(entries, list):
                logger.warning("No entries in webhook data")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            changes = entries[0].get("changes", [])
            if not changes or not isinstance(changes, list):
                logger.warning("No changes in webhook data")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Check for mock testing mode
            is_mock_testing = request.headers.get('X-Mock-Testing') == 'true'

            # Get the raw payload and value
            value = changes[0].get("value", {})
            if not value or not isinstance(value, dict):
                logger.warning("Invalid value format")
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
                        logger.warning(f"Mismatched WhatsApp phone_number_id: {metadata.get('phone_number_id')}")
                        return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Handle WhatsApp status updates
                if value.get("statuses"):
                    logger.info("Received WhatsApp status update")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Get WhatsApp contact info
                contacts = value.get("contacts", [])
                if not contacts or not isinstance(contacts, list):
                    logger.warning("No WhatsApp contacts in value")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                contact = contacts[0]
                if not contact or not isinstance(contact, dict):
                    logger.warning("Invalid WhatsApp contact information")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                channel_id = contact.get("wa_id")
                if not channel_id:
                    logger.warning("No WhatsApp channel ID in contact")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Check for SMS payload (stub for future implementation)
            elif "sms_provider" in value:
                channel_type = ChannelType.SMS
                logger.info("SMS channel not yet implemented")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Unknown channel type
            else:
                logger.warning("Unknown message channel type")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Validate we got the required information
            if not all([channel_type, channel_id]):
                logger.warning("Missing required message information")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Initialize state manager
            state_manager = StateManager(f"channel:{channel_id}")

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
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                return JsonResponse(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
            return JsonResponse(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, *args, **kwargs):
        logger.info(f"Webhook verification request: {request.query_params}")
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
        logger.info("Received send message request")

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

            # Initialize state manager for channel
            state_manager = StateManager(f"channel:{request.data['phoneNumber']}")

            # Get messaging service for channel
            service = get_messaging_service(state_manager, channel_type)

            # Send through service
            response = service.send_message(message)
            return JsonResponse(response.to_dict(), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
