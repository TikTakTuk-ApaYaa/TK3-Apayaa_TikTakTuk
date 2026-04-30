from django.shortcuts import render


def login_view(request):
    """Halaman login demo untuk checkpoint frontend."""
    return render(request, 'login.html')

def pilih_role(request):
    """Halaman awal untuk memilih apakah ingin daftar sebagai Customer atau Organizer"""
    return render(request, 'Cpengguna_pilihRole.html')

def registrasi_customer(request):
    """Halaman form pendaftaran khusus untuk Customer"""
    return render(request, 'Cpengguna_registCust.html')

def registrasi_organizer(request):
    """Halaman form pendaftaran khusus untuk Event Organizer"""
    return render(request, 'Cpengguna_registOrganizer.html')

def registrasi_administrator(request):
    """Halaman form pendaftaran khusus untuk Event Organizer"""
    return render(request, 'Cpengguna_registAdministrator.html')
