from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_menu, name='main_menu'),
]
# this maps the root URL to our main menu