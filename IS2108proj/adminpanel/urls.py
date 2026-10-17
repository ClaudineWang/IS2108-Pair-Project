from django.urls import path
from . import views
app_name = 'adminpanel'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:product_id>/update/', views.product_update, name='product_update'),
    path('inventory', views.inventory_list, name= 'inventory_list'),
    path('inventory/<int:product_id>/update/', views.inventory_update, name='inventory_update'),
]