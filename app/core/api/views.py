"""Cloud API webhook views"""
import logging
import sys

from core.api.models import Message as DBMessage  # Rename to avoid confusion
from core.config.state_manager import StateManager
from core.messaging.types import (
    ChannelIdentifier,
    ChannelType,
    Message as DomainMessage,
    MessageRecipient,
    TemplateContent
)
from decouple import config
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from services.messaging.service import MessagingService
from services.whatsapp.service import WhatsAppMessagingService

# Configure logging with a standardized format
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {"asctime": "%(asctime)s", "levelname": "%(levelname)s", "name": "%(name)s", "message": "%(message)s", "taskName": null}',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


# Initialize messaging service
whatsapp_service = WhatsAppMessagingService()
messaging_service = MessagingService(whatsapp_service)


class CredexCloudApiWebhook(APIView):
    """Cloud Api Webhook"""

    permission_classes = []
    parser_classes = (JSONParser,)
    throttle_classes = []  # Disable throttling for webhook endpoint

    @staticmethod
    def post(request):
        try:
            logger.info("Received webhook request")

            # Log full request data for debugging
            logger.debug(f"Full webhook payload: {request.data}")

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

            # Get the raw payload
            payload = changes[0].get("value", {})
            if not payload or not isinstance(payload, dict):
                logger.warning("Invalid payload format")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Identify channel type from payload/headers and validate
            channel_type = None
            channel_id = None
            message_type = None
            message_text = None

            # Check for WhatsApp payload
            if "messaging_product" in payload and payload["messaging_product"] == "whatsapp":
                channel_type = ChannelType.WHATSAPP

                # Validate WhatsApp payload
                if not is_mock_testing:
                    metadata = payload.get("metadata", {})
                    if not metadata or metadata.get("phone_number_id") != config("WHATSAPP_PHONE_NUMBER_ID"):
                        logger.warning(f"Mismatched WhatsApp phone_number_id: {metadata.get('phone_number_id')}")
                        return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Handle WhatsApp status updates
                if payload.get("statuses"):
                    logger.info("Received WhatsApp status update")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Get WhatsApp message
                messages = payload.get("messages", [])
                if not messages or not isinstance(messages, list):
                    logger.info("No WhatsApp messages in payload")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                message = messages[0]
                if not isinstance(message, dict):
                    logger.warning("Invalid WhatsApp message format")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Handle WhatsApp system messages
                if message.get("type") == "system" or message.get("system"):
                    logger.info("Ignoring WhatsApp system message")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Get WhatsApp contact info
                contacts = payload.get("contacts", [])
                if not contacts or not isinstance(contacts, list):
                    logger.warning("No WhatsApp contacts in payload")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                contact = contacts[0]
                if not contact or not isinstance(contact, dict):
                    logger.warning("Invalid WhatsApp contact information")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                channel_id = contact.get("wa_id")
                if not channel_id:
                    logger.warning("No WhatsApp channel ID in contact")
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

                # Get WhatsApp message type and text
                message_type = message.get("type")
                if message_type == "text":
                    text = message.get("text", {})
                    if isinstance(text, dict):
                        message_text = text.get("body", "")
                elif message_type == "interactive":
                    interactive = message.get("interactive", {})
                    if isinstance(interactive, dict):
                        if "button_reply" in interactive:
                            button_reply = interactive["button_reply"]
                            if isinstance(button_reply, dict):
                                message_text = button_reply.get("id", "")
                        elif "list_reply" in interactive:
                            list_reply = interactive["list_reply"]
                            if isinstance(list_reply, dict):
                                message_text = list_reply.get("id", "")
                        else:
                            logger.warning(f"Unhandled WhatsApp interactive type: {interactive}")
                            message_text = str(interactive)

            # Check for SMS payload (stub for future implementation)
            elif "sms_provider" in payload:
                channel_type = ChannelType.SMS
                # TODO: Add SMS-specific payload parsing
                # channel_id = payload.get("from")
                # message_type = "text"
                # message_text = payload.get("text")
                logger.info("SMS channel not yet implemented")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Unknown channel type
            else:
                logger.warning("Unknown message channel type")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Validate we got the required information
            if not all([channel_type, channel_id, message_type]):
                logger.warning("Missing required message information")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Initialize state manager with channel info (SINGLE SOURCE OF TRUTH)
            logger.info(f"Initializing state manager for {channel_type.value} channel: {channel_id}")
            state_manager = StateManager(f"channel:{channel_id}")

            # Log message details
            logger.info(f"Processing {channel_type.value} message: {message_text}")

            try:
                logger.info("Processing message...")
                # Process message through service
                response = messaging_service.handle_message(
                    state_manager=state_manager,
                    message_type=message_type,
                    message_text=message_text
                )

                # Convert domain Message to transport format at boundary
                if isinstance(response, DomainMessage):
                    response_dict = response.to_dict()
                else:
                    logger.error("Invalid response type from messaging service")
                    raise ValueError("Messaging service returned invalid response type")

                # For mock testing return the formatted response
                if is_mock_testing:
                    return JsonResponse(response_dict, status=status.HTTP_200_OK)

                # For real requests send via service
                messaging_service.send_message(response)
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


class WelcomeMessage(APIView):
    """Message"""

    parser_classes = (JSONParser,)

    @staticmethod
    def post(request):
        if request.data.get("message"):
            if not DBMessage.objects.all().first():
                DBMessage.objects.create(messsage=request.data.get("message"))
            else:
                obj = DBMessage.objects.all().first()
                obj.messsage = request.data.get("message")
                obj.save()
        return JsonResponse({"message": "Success"}, status=status.HTTP_200_OK)


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

            # Send through service
            response = messaging_service.send_message(message)
            return JsonResponse(response.to_dict(), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
