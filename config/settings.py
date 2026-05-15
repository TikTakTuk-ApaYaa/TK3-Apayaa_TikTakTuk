import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# --- 1. SECURITY SETTINGS ---
# Mengambil dari Render Environment Variables
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-lokal-aja')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Jika di lokal pakai '*', jika di Render pakai domain kamu
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# --- 2. DATABASE SETTINGS ---
# dj_database_url otomatis membaca variabel 'DATABASE_URL' di Render
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://postgres.kmyshghsxqwwngvzyijs:tiktaktuk-apayaa@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres',
        conn_max_age=600
    )
}

# Tambahkan opsi search_path (public penting agar session django jalan)
DATABASES['default']['OPTIONS'] = {'options': '-c search_path=tiktaktuk,public'}

# --- 3. APP DEFINITION ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'fitur_wajib',
    'fitur_merah',
    'fitur_kuning',
    'fitur_hijau',
    'fitur_biru',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', 
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- 4. LAINNYA ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'fitur_wajib:login'