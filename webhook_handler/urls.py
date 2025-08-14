from django.urls import path

from . import views

urlpatterns = [
  path("hello_function", views.hello_world),
  path("hello_class", views.HelloWorldView.as_view()),
]