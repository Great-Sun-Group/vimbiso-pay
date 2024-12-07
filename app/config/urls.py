from core.api.tests import test_integrations
from core.api.views import (
    CredexCloudApiWebhook,
    CredexSendMessageWebhook,
    WelcomeMessage,
    WipeCache,
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


# Health check endpoint with improved error handling and logging
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    try:
        # Test Redis connectivity with timeout
        cache.set("health_check", "ok", 10)
        result = cache.get("health_check")
        if result != "ok":
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Redis connectivity check failed",
                    "detail": "Cache set/get operation failed",
                },
                status=500,
            )

        # Return success response
        return JsonResponse(
            {"status": "ok", "message": "Service is healthy", "redis": "connected"}
        )
    except Exception as e:
        import logging

        logger = logging.getLogger("django")
        logger.error(f"Health check failed: {str(e)}", exc_info=True)

        return JsonResponse(
            {"status": "error", "message": "Health check failed", "detail": str(e)},
            status=500,
        )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("api/test-integrations/", test_integrations, name="test_integrations"),
    # Bot endpoints
    path("bot/webhook", CredexCloudApiWebhook.as_view(), name="webhook"),
    path("bot/notify", CredexSendMessageWebhook.as_view(), name="notify"),
    path("bot/welcome/message", WelcomeMessage.as_view(), name="welcome_message"),
    path("bot/wipe", WipeCache.as_view(), name="wipe"),
]

if settings.DEBUG:
    import debug_toolbar  # type: ignore

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
