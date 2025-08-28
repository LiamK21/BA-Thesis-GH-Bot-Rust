from django.urls import include, path

from webhook_handler.webhook import github_webhook

urlpatterns = [
    path("", github_webhook, name="github_webhook"),
]
