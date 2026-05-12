from django.urls import path
from . import views

app_name = 'fitur_wajib'

urlpatterns = [
    path('login/', views.login, name='login'),
    path('pilih-role/', views.pilih_role, name='pilih_role'),
    path('registrasi/customer/', views.registrasi_customer, name='regist_cust'),
    path('registrasi/organizer/', views.registrasi_organizer, name='regist_organizer'),
    path('registrasi/administrator/', views.registrasi_administrator, name='regist_admin'),
    path('', views.dashboard, name='dashboard'), 
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/update-password/', views.profile_update_password, name='profile_update_password'),
]