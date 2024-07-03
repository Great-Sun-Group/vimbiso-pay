from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from bot.views import CredexCloudApiWebhook, CredexSendMessageWebhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/webhook', CredexCloudApiWebhook.as_view(), name="webhook"),
    path('bot/message', CredexSendMessageWebhook.as_view(), name="message"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
