from django.urls import path
from . import views

app_name = 'fitur_wajib'

urlpatterns = [
    # --- Auth System ---
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # --- Registration System ---
    path('pilih-role/', views.pilih_role, name='pilih_role'),
    path('register/customer/', views.registrasi_customer, name='registrasi_customer'),
    path('register/organizer/', views.registrasi_organizer, name='registrasi_organizer'),
    path('register/admin/', views.registrasi_administrator, name='registrasi_administrator'),
    
    # --- User Features ---
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/update-password/', views.profile_update_password, name='profile_update_password'),
]