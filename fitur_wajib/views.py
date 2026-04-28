from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def pilih_role(request):
    """Halaman awal untuk memilih apakah ingin daftar sebagai Customer atau Organizer"""
    return render(request, 'Cpengguna_pilihRole.html')

def registrasi_customer(request):
    """Halaman form pendaftaran khusus untuk Customer"""
    return render(request, 'Cpengguna_registCust.html')

def registrasi_organizer(request):
    """Halaman form pendaftaran khusus untuk Event Organizer"""
    return render(request, 'Cpengguna_registOrganizer.html')