from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls), 
    path('', include('fitur_biru.urls')), 
    path('', include('fitur_merah.urls')),
    path('', include('fitur_kuning.urls')),
    path('', include('fitur_hijau.urls')),
    path('', include('fitur_wajib.urls')),
]