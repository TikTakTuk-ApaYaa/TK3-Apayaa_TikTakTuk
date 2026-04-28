from django.urls import path
from . import views

app_name = 'fitur_wajib'

urlpatterns = [
    path('pilih-role/', views.pilih_role, name='pilih_role'),
    path('registrasi/customer/', views.registrasi_customer, name='regist_cust'),
    path('registrasi/organizer/', views.registrasi_organizer, name='regist_organizer'),
]