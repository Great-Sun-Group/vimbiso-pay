"""Integration tests for core API"""
from django.http import JsonResponse
from django.core.cache import cache
import requests
from decouple import config
import logging

logger = logging.getLogger(__name__)

# Test message formats for different channels
TEST_MESSAGES = {
    "whatsapp": {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "test",
        "type": "text",
        "text": {"body": "test"}
    },
    "sms": {
        "sms_provider": "test",
        "from": "test",
        "to": "test",
        "text": "test"
    }
}

# Channel-specific environment variables
CHANNEL_ENV_VARS = {
    "whatsapp": [
        "WHATSAPP_API_URL",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_ACCESS_TOKEN"
    ],
    "sms": [
        "SMS_API_URL",
        "SMS_API_KEY",
        "SMS_FROM_NUMBER"
    ]
}

# Channel-specific message format requirements
CHANNEL_MESSAGE_REQUIREMENTS = {
    "whatsapp": ["messaging_product", "to", "type"],
    "sms": ["sms_provider", "from", "to", "text"]
}


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

    # Test 4: Messaging Channels
    for channel, test_message in TEST_MESSAGES.items():
        try:
            # Verify channel configuration
            required_vars = CHANNEL_ENV_VARS.get(channel, [])
            for var in required_vars:
                if not config(var, default=None):
                    raise ValueError(f"Missing required environment variable: {var}")

            # Verify message format
            required_fields = CHANNEL_MESSAGE_REQUIREMENTS.get(channel, [])
            if not all(k in test_message for k in required_fields):
                raise ValueError(f"Invalid {channel} message format")

            results["tests"][channel] = {
                "status": "success",
                "message": f"{channel.upper()} configuration verified",
            }
        except Exception as e:
            results["tests"][channel] = {
                "status": "error",
                "message": f"{channel.upper()} configuration error: {str(e)}",
            }

    # Overall status
    if all(test["status"] == "success" for test in results["tests"].values()):
        results["status"] = "success"
    else:
        results["status"] = "error"

    return JsonResponse(results)
