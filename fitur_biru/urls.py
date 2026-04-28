from django.urls import path
from . import views

urlpatterns = [
    # Order Paths
    path('order/create/', views.create_order, name='create_order'),
    path('order/admin/', views.read_order_admin, name='read_order_admin'),
    path('order/my/', views.read_order_cust, name='read_order_cust'),
    path('order/organizer/', views.read_order_organizer, name='read_order_organizer'),

    # Promo Paths
    path('promo/admin/', views.crud_promo_admin, name='crud_promo_admin'),
    path('promo/customer/', views.read_promo_cust, name='read_promo_cust'),
    path('promo/organizer/', views.read_promo_organizer, name='read_promo_organizer'),
    path('promo/guest/', views.read_promo_guest, name='read_promo_guest'),
]