from django.urls import path
from . import views

app_name = "customer"

urlpatterns = [
    path("signup/", views.customer_signup, name="customer_signup"),
    path("login/", views.customer_login, name="customer_login"),
]