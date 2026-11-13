from django.urls import path
from . import views

app_name = "customer"

urlpatterns = [
    path("home/", views.customer_home, name="customer_home"),
    path("recommendations/", views.customer_recommendations, name="recommendations"),
    path("signup/", views.customer_signup, name="customer_signup"),
    path("login/", views.customer_login, name="customer_login"),
    path("onboarding/", views.customer_onboarding, name="customer_onboarding"),
    path("questionnaire/", views.customer_questionnaire, name="customer_questionnaire"),
    path("profile/", views.customer_profile, name="customer_profile"),
    path("orders/", views.order_tracking, name="order_tracking"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/reorder/", views.order_again, name="order_again"),
]
