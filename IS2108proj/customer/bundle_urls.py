from django.urls import path

from . import views

app_name = "bundles"

urlpatterns = [
    path("", views.subscription_bundle_list, name="list"),
    path("<int:bundle_id>/", views.subscription_bundle_detail, name="detail"),
    path("<int:bundle_id>/subscribe/", views.subscribe_to_bundle, name="subscribe"),
    path("subscriptions/<int:subscription_id>/cancel/", views.cancel_subscription, name="cancel"),
]
