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

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
        # Early debug logging
        logger.debug("==== START OF WEBHOOK REQUEST ====")
        logger.debug(f"Request META: {request.META}")
        logger.debug(f"Request Headers: {request.headers}")
        logger.debug(f"Request Body: {request.body}")

        try:
            logger.info("Received webhook request")
            logger.debug(f"Request data: {request.data}")

            # Get the WhatsApp payload
            payload = request.data.get("entry")[0].get("changes")[0].get("value")
            logger.info(f"Webhook payload metadata: {payload.get('metadata', {})}")

            # Check for mock testing header
            is_mock_testing = request.headers.get('X-Mock-Testing', '').lower() == 'true'
            logger.debug(f"Mock testing mode: {is_mock_testing}")

            # Only validate phone_number_id for real WhatsApp requests
            if not is_mock_testing:
                if payload["metadata"]["phone_number_id"] != config(
                    "WHATSAPP_PHONE_NUMBER_ID"
                ):
                    logger.warning(
                        f"Mismatched phone_number_id: {payload['metadata']['phone_number_id']}"
                    )
                    return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            if not payload.get("messages"):
                logger.info("No messages in payload")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            message = payload["messages"][0]
            message_type = message["type"]

            # Handle system messages
            if (message_type == "system" or message.get("system") or
                    (not is_mock_testing and payload["metadata"]["phone_number_id"] != config("WHATSAPP_PHONE_NUMBER_ID"))):
                logger.info("Ignoring system message")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Get contact info
            contact = payload["contacts"][0] if message_type != "system" else message.get("wa_id")
            if not contact:
                logger.warning("No contact information in payload")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Debug Redis connection
            logger.info("Testing Redis connection...")
            try:
                test_key = "test_redis_connection"
                cache.set(test_key, "test_value", timeout=10)
                test_value = cache.get(test_key)
                logger.info(f"Redis test - Set and get successful: {test_value}")
            except Exception as e:
                logger.error(f"Redis connection error: {str(e)}")
                return JsonResponse(
                    {"error": "Redis connection failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Create CachedUser with debug logging
            logger.info(f"Creating CachedUser for phone: {contact['wa_id']}")
            user = CachedUser(contact["wa_id"])
            logger.info(f"CachedUser created with state: {user.state.__dict__}")

            state = user.state

            # Check message age
            message_stamp = datetime.fromtimestamp(int(message["timestamp"]))
            if (datetime.now() - message_stamp).total_seconds() > 20:
                logger.info(f"Ignoring old webhook from {message_stamp}")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Extract message text for logging
            message_text = ""
            if message_type == "text":
                message_text = message["text"]["body"]
            elif message_type == "interactive":
                interactive = message.get("interactive", {})
                if "button_reply" in interactive:
                    message_text = interactive["button_reply"]["id"]
                elif "list_reply" in interactive:
                    message_text = interactive["list_reply"]["id"]
                else:
                    # Log full interactive message for debugging
                    logger.debug(f"Unhandled interactive message type: {interactive}")
                    message_text = str(interactive)

            logger.info(
                f"Credex [{state.stage}<|>{state.option}] RECEIVED -> {message_text} "
                f"FROM {contact['wa_id']} @ {message_stamp}"
            )

            try:
                logger.info("Creating CredexBotService...")
                # Pass the original WhatsApp format request data
                service = CredexBotService(payload=request.data, user=user)

                # For mock testing return the response directly
                if is_mock_testing:
                    logger.info("Mock testing mode: Returning response without sending to WhatsApp")
                    return JsonResponse({"response": service.response}, status=status.HTTP_200_OK)

                # For real requests send via WhatsApp
                logger.info("Sending response via WhatsApp service...")
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
        from django.core.cache import cache

        cache.delete(request.data.get("number"))
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
