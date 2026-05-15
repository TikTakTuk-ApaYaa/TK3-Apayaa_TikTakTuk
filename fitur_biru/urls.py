
from django.urls import path
from . import views as v   # sesuaikan nama module

app_name = 'fitur_biru' 

urlpatterns = [
    # ---- ORDER ----
    # Customer: lihat pesanan sendiri
    path('orders/',                         v.read_order_customer,  name='read_order_customer'),
    # Organizer: lihat pesanan event-nya
    path('orders/organizer/',               v.read_order_organizer, name='read_order_organizer'),
    # Admin: lihat semua pesanan
    path('orders/admin/',                   v.read_order_admin,     name='read_order_admin'),
    # Admin: update status pembayaran
    path('orders/admin/<uuid:order_id>/update/',  v.update_order_admin, name='update_order_admin'),
    # Admin: hapus order
    path('orders/admin/<uuid:order_id>/delete/',  v.delete_order_admin, name='delete_order_admin'),
    # Customer: beli tiket (checkout)
    path('events/<uuid:event_id>/checkout/', v.create_order,        name='create_order'),

    # ---- PROMOTION ----
    # Semua role: lihat daftar promosi
    path('promotions/',                     v.read_promotion,       name='read_promotion'),
    # Admin: buat promosi baru
    path('promotions/create/',              v.create_promotion,     name='create_promotion'),
    # Admin: update promosi
    path('promotions/<uuid:promotion_id>/update/', v.update_promotion, name='update_promotion'),
    # Admin: hapus promosi
    path('promotions/<uuid:promotion_id>/delete/', v.delete_promotion, name='delete_promotion'),
]