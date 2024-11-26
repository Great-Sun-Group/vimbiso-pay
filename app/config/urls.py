from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.api.views import (
    CredexCloudApiWebhook,
    CredexSendMessageWebhook,
    WelcomeMessage,
    WipeCache
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('bot/webhook', CredexCloudApiWebhook.as_view(), name="webhook"),
    path('bot/notify', CredexSendMessageWebhook.as_view(), name="notify"),
    path('bot/welcome/message', WelcomeMessage.as_view(), name="welcome_message"),
    path('bot/wipe', WipeCache.as_view(), name="wipe"),
]

if settings.DEBUG:
    import debug_toolbar  # type: ignore

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
