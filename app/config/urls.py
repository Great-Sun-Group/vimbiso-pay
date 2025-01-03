from core.api.tests import test_integrations
from core.api.views import (CredexCloudApiWebhook, CredexSendMessageWebhook,
                            WelcomeMessage, WipeCache)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import include, path
from django.views import defaults
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from core.utils.throttling import HealthCheckRateThrottle
from core.utils.redis_atomic import AtomicStateManager
import redis

from api import views

# Error handlers
handler400 = defaults.bad_request
handler403 = defaults.permission_denied
handler404 = defaults.page_not_found
handler500 = defaults.server_error

# Initialize Redis clients
state_redis_client = redis.from_url(settings.REDIS_STATE_URL)
state_redis = AtomicStateManager(state_redis_client).redis


# Health check endpoint with improved error handling and logging
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([HealthCheckRateThrottle])
def health_check(request):
    status_info = {
        "status": "ok",
        "message": "Service is healthy",
        "components": {
            "cache_redis": "unknown",
            "state_redis": "unknown"
        }
    }

    # Check cache Redis
    try:
        cache.set("health_check", "ok", 10)
        result = cache.get("health_check")
        status_info["components"]["cache_redis"] = "connected" if result == "ok" else "error"
    except Exception as e:
        import logging
        logger = logging.getLogger("django")
        logger.warning(f"Cache Redis check failed: {str(e)}")
        status_info["components"]["cache_redis"] = "error"

    # Check state Redis using AtomicStateManager's client
    try:
        state_redis.set("health_check", "ok", 10)
        result = state_redis.get("health_check")
        status_info["components"]["state_redis"] = "connected" if result == "ok" else "error"
    except Exception as e:
        import logging
        logger = logging.getLogger("django")
        logger.warning(f"State Redis check failed: {str(e)}")
        status_info["components"]["state_redis"] = "error"

    # Determine overall status
    if all(v == "connected" for v in status_info["components"].values()):
        status_info["status"] = "ok"
        return JsonResponse(status_info)
    elif all(v == "error" for v in status_info["components"].values()):
        status_info["status"] = "error"
        status_info["message"] = "All Redis connections failed"
        return JsonResponse(status_info, status=500)
    else:
        status_info["status"] = "degraded"
        status_info["message"] = "Some Redis connections failed"
        return JsonResponse(status_info, status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("api/test-integrations/", test_integrations, name="test_integrations"),
    # Bot endpoints
    path("bot/webhook", CredexCloudApiWebhook.as_view(), name="webhook"),
    path("bot/notify", CredexSendMessageWebhook.as_view(), name="notify"),
    path("bot/welcome/message", WelcomeMessage.as_view(), name="welcome_message"),
    path("bot/wipe", WipeCache.as_view(), name="wipe"),
    # API endpoints
    path("api/webhooks/", views.webhook_endpoint, name="webhook-endpoint"),
    # Company endpoints
    path("api/companies/", views.list_companies, name="company-list"),
    path("api/companies/<str:company_id>/", views.get_company, name="company-detail"),
    # Member endpoints
    path("api/members/", views.list_members, name="member-list"),
    path("api/members/<str:member_id>/", views.get_member, name="member-detail"),
    # Offer endpoints
    path("api/offers/", views.list_offers, name="offer-list"),
    path("api/offers/<str:offer_id>/", views.get_offer, name="offer-detail"),
    path("api/offers/<str:offer_id>/accept/", views.accept_offer, name="offer-accept"),
    path("api/offers/<str:offer_id>/reject/", views.reject_offer, name="offer-reject"),
]

if settings.DEBUG:
    import debug_toolbar  # type: ignore

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
