from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

# Create your views here.

def hello_world(request):
    return HttpResponse("Hello, World! This is a simple Django view.")
  
  
class HelloWorldView(View):
    def get(self, request):
        return HttpResponse("Hello, World! This is a class-based view.")