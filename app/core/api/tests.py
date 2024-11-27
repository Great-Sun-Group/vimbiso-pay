from django.http import JsonResponse
from django.core.cache import cache
import requests
from decouple import config
import logging
from ..utils.utils import CredexWhatsappService

logger = logging.getLogger(__name__)


def test_integrations(request):
    """
    Test endpoint to verify all integrations are working correctly.
    GET /api/test-integrations/
    """
    results = {"status": "running", "tests": {}}

    # Test 1: Django Setup
    results["tests"]["django"] = {
        "status": "success",
        "message": "Django is running correctly",
    }

    # Test 2: Redis Connection
    try:
        cache.set("test_key", "test_value", 10)
        test_value = cache.get("test_key")
        if test_value == "test_value":
            results["tests"]["redis"] = {
                "status": "success",
                "message": "Redis connection successful",
            }
        else:
            raise Exception("Redis get/set test failed")
    except Exception as e:
        results["tests"]["redis"] = {
            "status": "error",
            "message": f"Redis connection failed: {str(e)}",
        }

    # Test 3: Credex Core API
    try:
        api_url = f"{config('MYCREDEX_APP_URL')}v1/health"
        response = requests.get(api_url)
        if response.status_code == 200:
            results["tests"]["credex_api"] = {
                "status": "success",
                "message": "Credex Core API connection successful",
            }
        else:
            raise Exception(f"API returned status code {response.status_code}")
    except Exception as e:
        results["tests"]["credex_api"] = {
            "status": "error",
            "message": f"Credex Core API connection failed: {str(e)}",
        }

    # Test 4: WhatsApp API
    try:
        # Create a test message that won't actually be sent
        test_service = CredexWhatsappService(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": "test",
                "type": "text",
                "text": {"body": "test"},
            },
            config("WHATSAPP_PHONE_NUMBER_ID"),
        )

        # Just verify we can construct the URL and headers
        url = (
            f"{config('WHATSAPP_API_URL')}{config('WHATSAPP_PHONE_NUMBER_ID')}/messages"
        )
        headers = {
            "Authorization": f"Bearer {config('WHATSAPP_ACCESS_TOKEN')}",
            "Content-Type": "application/json",
        }

        results["tests"]["whatsapp"] = {
            "status": "success",
            "message": "WhatsApp configuration verified",
        }
    except Exception as e:
        results["tests"]["whatsapp"] = {
            "status": "error",
            "message": f"WhatsApp configuration error: {str(e)}",
        }

    # Overall status
    if all(test["status"] == "success" for test in results["tests"].values()):
        results["status"] = "success"
    else:
        results["status"] = "error"

    return JsonResponse(results)
