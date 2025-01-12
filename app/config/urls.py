from core.api.views import (CredexCloudApiWebhook, CredexSendMessageWebhook,
                            WipeCache, HealthCheck)
from django.urls import path

urlpatterns = [
    path("health/", HealthCheck.as_view(), name="health_check"),
    # Bot endpoints
    path("bot/webhook", CredexCloudApiWebhook.as_view(), name="webhook"),
    path("bot/notify", CredexSendMessageWebhook.as_view(), name="notify"),
    path("bot/wipe", WipeCache.as_view(), name="wipe"),
]
