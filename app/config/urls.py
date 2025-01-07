from core.api.views import (CredexCloudApiWebhook, CredexSendMessageWebhook,
                            WipeCache)
from django.http import JsonResponse
from django.urls import path
from django.core.cache import caches


def health_check(request):
    """Simple health check endpoint"""
    try:
        # Check state Redis
        default_cache = caches['default']
        default_cache.set("health_check", "ok", 10)
        result = default_cache.get("health_check")

        if result == "ok":
            return JsonResponse({"status": "ok", "message": "Service is healthy"})
        else:
            return JsonResponse(
                {"status": "error", "message": "Redis state check failed"},
                status=500
            )
    except Exception as e:
        import logging
        logger = logging.getLogger("django")
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": str(e)},
            status=500
        )


urlpatterns = [
    path("health/", health_check, name="health_check"),
    # Bot endpoints
    path("bot/webhook", CredexCloudApiWebhook.as_view(), name="webhook"),
    path("bot/notify", CredexSendMessageWebhook.as_view(), name="notify"),
    path("bot/wipe", WipeCache.as_view(), name="wipe"),
]
