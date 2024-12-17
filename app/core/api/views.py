"""Cloud API webhook views"""
import logging
import sys
from datetime import datetime

from core.api.models import Message
from core.config.constants import CachedUser
from core.utils.utils import CredexWhatsappService
from decouple import config
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from services.whatsapp.handler import CredexBotService

# Configure logging with a standardized format
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {"asctime": "%(asctime)s", "levelname": "%(levelname)s", "name": "%(name)s", "message": "%(message)s", "taskName": null}',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


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

            # Get the WhatsApp payload
            payload = changes[0].get("value", {})
            if not payload or not isinstance(payload, dict):
                logger.warning("Invalid payload format")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            logger.info(f"Webhook payload metadata: {payload.get('metadata', {})}")

            # Check for mock testing mode
            is_mock_testing = request.headers.get('X-Mock-Testing') == 'true'

            # Only validate phone_number_id for real WhatsApp requests
            if not is_mock_testing:
                metadata = payload.get("metadata", {})
                if not metadata or metadata.get("phone_number_id") != config("WHATSAPP_PHONE_NUMBER_ID"):
                    logger.warning(
                        f"Mismatched phone_number_id: {metadata.get('phone_number_id')}"
                    )
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Handle status updates
            if payload.get("statuses"):
                logger.info("Received status update")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Handle messages
            messages = payload.get("messages", [])
            if not messages or not isinstance(messages, list):
                logger.info("No messages in payload")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            message = messages[0]
            if not isinstance(message, dict):
                logger.warning("Invalid message format")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            message_type = message.get("type")
            if not message_type:
                logger.warning("No message type specified")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Handle system messages
            if (message_type == "system" or message.get("system") or
                    (not is_mock_testing and payload["metadata"]["phone_number_id"] != config("WHATSAPP_PHONE_NUMBER_ID"))):
                logger.info("Ignoring system message")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Get contact info
            contacts = payload.get("contacts", [])
            if not contacts or not isinstance(contacts, list):
                logger.warning("No contacts in payload")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            contact = contacts[0] if message_type != "system" else message.get("wa_id")
            if not contact or not isinstance(contact, dict):
                logger.warning("Invalid contact information")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            wa_id = contact.get("wa_id")
            if not wa_id:
                logger.warning("No WA ID in contact")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Initialize or get cached user - this handles all state management
            logger.info(f"Initializing CachedUser for phone: {wa_id}")
            user = CachedUser(wa_id)
            state = user.state

            logger.info(f"Using CachedUser with state: {state.__dict__}")

            # Check message age
            timestamp = message.get("timestamp")
            if not timestamp:
                logger.warning("No timestamp in message")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            message_stamp = datetime.fromtimestamp(int(timestamp))
            if (datetime.now() - message_stamp).total_seconds() > 20:
                logger.info(f"Ignoring old webhook from {message_stamp}")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Extract message text for logging
            message_text = ""
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
                        # Log full interactive message for debugging
                        logger.debug(f"Unhandled interactive message type: {interactive}")
                        message_text = str(interactive)

            # Get flow data from state
            flow_data = state.state.get("flow_data", {}) or {}
            stage = flow_data.get("stage", "START")
            option = flow_data.get("option", "NONE")

            logger.info(
                f"Credex [{stage}<|>{option}] RECEIVED -> {message_text} "
                f"FROM {wa_id} @ {message_stamp}"
            )

            try:
                logger.info("Creating CredexBotService...")
                # Create bot service with cached CredEx service
                service = CredexBotService(payload=request.data, user=user)

                # For mock testing return the response directly
                if is_mock_testing:
                    return JsonResponse(service.response, status=status.HTTP_200_OK)

                # For real requests send via WhatsApp
                response = CredexWhatsappService(
                    payload=service.response,
                    phone_number_id=payload["metadata"]["phone_number_id"]
                ).send_message()
                logger.info(f"WhatsApp API Response: {response}")
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
            if not Message.objects.all().first():
                Message.objects.create(messsage=request.data.get("message"))
            else:
                obj = Message.objects.all().first()
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
    """Cloud Api Webhook"""

    parser_classes = (JSONParser,)
    throttle_classes = []  # Disable throttling for webhook endpoint

    @staticmethod
    def post(request):
        logger.info("Received send message request")
        if (
            request.headers.get("whatsappBotAPIkey", "").lower()
            == config("CLIENT_API_KEY").lower()
        ):
            if (
                request.data.get("phoneNumber")
                and request.data.get("memberName")
                and request.data.get("message")
            ):
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": request.data.get("phoneNumber"),
                    "type": "template",
                    "template": {
                        "name": "incoming_notification",
                        "language": {"code": "en_US"},
                        "components": [
                            {
                                "type": "body",
                                "parameters": [
                                    {
                                        "type": "text",
                                        "text": request.data.get("memberName")
                                    },
                                    {
                                        "type": "text",
                                        "text": request.data.get("message")
                                    }
                                ]
                            }
                        ]
                    }
                }

                response = CredexWhatsappService(payload=payload).notify()
                logger.info(f"WhatsApp API Response: {response}")
                return JsonResponse(response, status=status.HTTP_200_OK)
        return JsonResponse(
            {"status": "Successful", "message": "Missing API KEY"},
            status=status.HTTP_400_BAD_REQUEST
        )
