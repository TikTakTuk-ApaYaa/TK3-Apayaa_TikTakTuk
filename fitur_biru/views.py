from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- VIEWS UNTUK ORDER ---

@login_required
def create_order(request):
    """Halaman Beli Tiket / Checkout"""
    return render(request, 'create_order.html')

@login_required
def read_order_admin(request):
    """Halaman Semua Order (Akses Admin)"""
    return render(request, 'read_order_admin.html')

@login_required
def read_order_cust(request):
    """Halaman Pesanan Saya (Akses Customer)"""
    return render(request, 'read_order_cust.html')

@login_required
def read_order_organizer(request):
    """Halaman Order Masuk (Akses Organizer)"""
    return render(request, 'read_order_organizer.html')


# --- VIEWS UNTUK PROMO ---

@login_required
def crud_promo_admin(request):
    """Halaman Manajemen Promo (Akses Admin)"""
    return render(request, 'CRUD_promo_admin.html')

@login_required
def read_promo_cust(request):
    """Halaman Daftar Promo (Akses Customer)"""
    return render(request, 'read_promo_cust.html')

@login_required
def read_promo_organizer(request):
    """Halaman Daftar Promo (Akses Organizer)"""
    return render(request, 'read_promo_organizer.html')

def read_promo_guest(request):
    """Halaman Promo untuk Pengunjung (Tanpa Login)"""
    return render(request, 'read_promo_guest.html')