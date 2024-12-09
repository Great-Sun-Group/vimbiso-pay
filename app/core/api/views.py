import json
import logging
import sys
from datetime import datetime

import requests
from core.api.models import Message
from core.config.constants import CachedUser
from services.whatsapp.handler import CredexBotService
from core.utils.utils import CredexWhatsappService
from decouple import config
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView

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

            if payload.get("messages"):
                phone_number_id = payload["metadata"].get("phone_number_id")
                message = payload["messages"][0]
                message_type = message["type"]
                contact = (
                    payload["contacts"][0]
                    if message_type != "system"
                    else payload["messages"][0].get("wa_id")
                )

                if (
                    message_type == "system"
                    or message.get("system")
                    or (not is_mock_testing and phone_number_id != config("WHATSAPP_PHONE_NUMBER_ID"))
                ):
                    logger.info("Ignoring system message")
                    return JsonResponse(
                        {"message": "received"}, status=status.HTTP_200_OK
                    )

                if message_type == "text":
                    payload["body"] = message["text"]["body"]

                elif message_type == "button":
                    payload["body"] = message["button"]["payload"]

                elif message_type == "interactive":
                    if message.get("interactive"):
                        if message["interactive"]["type"] == "button_reply":
                            payload["body"] = message["interactive"]["button_reply"][
                                "id"
                            ]
                        elif message["interactive"].get("type") == "nfm_reply":
                            message_type = "nfm_reply"
                            payload["body"] = json.loads(
                                message["interactive"]["nfm_reply"]["response_json"]
                            )
                        else:
                            payload["body"] = message["interactive"]["list_reply"]["id"]
                    else:
                        return JsonResponse(
                            {"message": "received"}, status=status.HTTP_200_OK
                        )
                elif message_type == "location":
                    payload["body"] = (
                        message["location"]["latitude"],
                        message["location"]["longitude"]
                    )

                elif message_type == "image":
                    image_id = message["image"]["id"]
                    headers = {
                        "Authorization": "Bearer " + config("WHATSAPP_ACCESS_TOKEN")
                    }
                    file = requests.request(
                        "GET",
                        url=f"https://graph.facebook.com/v20.0/{image_id}",
                        headers=headers,
                        data={}
                    ).json()

                    caption = message["image"].get("caption")
                    payload["file_id"] = image_id
                    if caption:
                        payload["caption"] = caption
                    payload["body"] = file.get("url")
                    payload["file_name"] = file.get("name")

                elif message_type == "document":
                    document_id = message["document"]["id"]
                    headers = {
                        "Authorization": "Bearer " + config("WHATSAPP_ACCESS_TOKEN")
                    }
                    file = requests.request(
                        "GET",
                        url=f"https://graph.facebook.com/v20.0/{document_id}",
                        headers=headers,
                        data={}
                    ).json()
                    payload["body"] = file.get("url")
                    payload["file_name"] = file.get("name")
                    payload["file_id"] = document_id

                elif message_type == "video":
                    video_id = message["video"]["id"]
                    headers = {
                        "Authorization": "Bearer " + config("WHATSAPP_ACCESS_TOKEN")
                    }
                    file = requests.request(
                        "GET",
                        url=f"https://graph.facebook.com/v20.0/{video_id}",
                        headers=headers,
                        data={}
                    ).json()
                    payload["body"] = file.get("url")
                    payload["file_name"] = file.get("name")
                    payload["file_id"] = video_id
                    caption = message["video"].get("caption")
                    if caption:
                        payload["caption"] = caption
                elif message_type == "audio":
                    audio_id = message["audio"]["id"]
                    headers = {
                        "Authorization": "Bearer " + config("WHATSAPP_ACCESS_TOKEN")
                    }
                    file = requests.request(
                        "GET",
                        url=f"https://graph.facebook.com/v20.0/{audio_id}",
                        headers=headers,
                        data={}
                    ).json()
                    payload["body"] = file.get("url")
                    payload["file_name"] = file.get("name")

                elif message_type == "order":
                    payload["body"] = message["order"]["product_items"]

                elif message_type == "nfm_reply":
                    payload["body"] = message["nfm_reply"]["response_json"]

                if f"{payload['body']}".lower() in ["ok", "thanks", "thank you"]:
                    logger.info("Sending thank you response")
                    CredexWhatsappService(
                        payload={
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": contact["wa_id"],
                            "type": "text",
                            "text": {"body": "🙏"}
                        },
                        phone_number_id=payload["metadata"]["phone_number_id"]
                    ).notify()

                    return JsonResponse(
                        {"message": "received"}, status=status.HTTP_200_OK
                    )

                elif message_type == "reaction":
                    payload["body"] = message["reaction"].get("emoji")
                    if f"{payload['body']}".lower() in [
                        "👍",
                        "🙏",
                        "❤️",
                        "ok",
                        "thanks",
                        "thank you"
                    ]:
                        logger.info("Sending reaction response")
                        CredexWhatsappService(
                            payload={
                                "messaging_product": "whatsapp",
                                "recipient_type": "individual",
                                "to": contact["wa_id"],
                                "type": "text",
                                "text": {"body": "🙏"}
                            },
                            phone_number_id=payload["metadata"]["phone_number_id"]
                        ).notify()
                        return JsonResponse(
                            {"message": "received"}, status=status.HTTP_200_OK
                        )

                if not contact:
                    logger.warning("No contact information in payload")
                    return JsonResponse(
                        {"message": "received"}, status=status.HTTP_200_OK
                    )

                # Format the message
                formatted_message = {
                    "to": payload["metadata"]["display_phone_number"],
                    "phone_number_id": payload["metadata"]["phone_number_id"],
                    "from": contact["wa_id"],
                    "username": contact["profile"]["name"],
                    "type": message_type,
                    "message": payload["body"],
                    "filename": payload.get("file_name", None),
                    "fileid": payload.get("file_id", None),
                    "caption": payload.get("caption", None)
                }

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
                logger.info(f"Creating CachedUser for phone: {formatted_message.get('from')}")
                user = CachedUser(formatted_message.get("from"))
                logger.info(f"CachedUser created with state: {user.state.__dict__}")

                state = user.state

                # Calculate the time difference in seconds
                message_stamp = datetime.fromtimestamp(int(message["timestamp"]))
                if (datetime.now() - message_stamp).total_seconds() > 20:
                    logger.info(f"Ignoring old webhook from {message_stamp}")
                    return JsonResponse(
                        {"message": "received"}, status=status.HTTP_200_OK
                    )

                logger.info(
                    f"Credex [{state.stage}<|>{state.option}] RECEIVED -> {payload['body']} "
                    f"FROM {formatted_message.get('from')} @ {message_stamp}"
                )

                try:
                    logger.info("Creating CredexBotService...")
                    service = CredexBotService(payload=formatted_message, user=user)

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
                    # Return error response instead of silently continuing
                    return JsonResponse(
                        {"error": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)
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
