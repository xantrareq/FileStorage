import os
from pathlib import Path
from decouple import config

# Стандартный путь к корню
BASE_DIR = Path(__file__).resolve().parent.parent

# Секретный ключ берем из .env
SECRET_KEY = config('SECRET_KEY')

DEBUG = True

# Домены, на которых проект будет крутиться
ALLOWED_HOSTS = ['127.0.0.1', '.herokuapp.com', '.onrender.com']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Основная логика тут
    'filemanager',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cloudstorage_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], 
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

# Для локальной разработки юзаем sqlite, для прода потом надо будет подумать о Postgres
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Статика
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Там загруженные файлы
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Таймзона
TIME_ZONE = 'Europe/Moscow'
USE_TZ = True

# Редиректы после входа/выхода
LOGIN_REDIRECT_URL = 'my_files'
LOGOUT_REDIRECT_URL = 'home'

# Шифрование (Fernet) 
# Ключ сервера для защиты пользовательских данных
MASTER_KEY_STR = config('MASTER_ENCRYPTION_KEY')
MASTER_ENCRYPTION_KEY = MASTER_KEY_STR.encode('utf-8')

# Валидация ключа: если в .env ключ неверной длины, то не запускается
if len(MASTER_ENCRYPTION_KEY) != 44:
    raise ValueError(
        "Ошибка в ключе шифрования! MASTER_ENCRYPTION_KEY должен быть 44 символа (base64)."
    )