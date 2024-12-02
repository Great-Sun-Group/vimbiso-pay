from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import AllowAny
from core.api.views import (
    CredexCloudApiWebhook,
    CredexSendMessageWebhook,
    WelcomeMessage,
    WipeCache,
)
from core.api.tests import test_integrations
from django.core.cache import cache


# Health check endpoint
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    try:
        # Test Redis connectivity
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        if result != 'ok':
            return JsonResponse({
                "status": "error",
                "message": "Redis connectivity check failed"
            }, status=500)
        return JsonResponse({
            "status": "ok",
            "message": "Service is healthy"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }, status=500)


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
