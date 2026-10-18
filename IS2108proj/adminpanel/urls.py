from django.urls import path
from . import views
app_name = 'adminpanel'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:product_id>/update/', views.product_update, name='product_update'),
    path('inventory/', views.inventory_list, name= 'inventory_list'),
    path('inventory/<int:product_id>/update/', views.inventory_update, name='inventory_update'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/update/', views.order_update, name='order_update'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:customer_id>/view/', views.customer_view, name= 'customer_view'),
    path('subscriptions/', views.subscription_bundle_list, name='subscription_bundle_list'),
    path('subscriptions/<int:subscription_bundle_id>/update/', views.subscription_bundle_update, name='subscription_bundle_update'),
    path('subscriptions/add/', views.subscription_bundle_add, name='subscription_bundle_add'),
    path('reviews/', views.review_list, name='review_list'),
    path('reviews/<int:review_id>/update/', views.review_update, name='review_update'),
    path('customer-subscriptions/', views.customer_subscription_list, name='customer_subscription_list'),
    path('customer-subscriptions/<int:subscription_id>/view/', views.customer_subscription_view, name='customer_subscription_view'),
]