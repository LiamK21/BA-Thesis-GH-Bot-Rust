from django.urls import include, path
from webhook import github_webhook

urlpatterns = [
    path("", github_webhook, name="github_webhook"),
]
