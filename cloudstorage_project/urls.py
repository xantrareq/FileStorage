# cloudstorage_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from filemanager import views as filemanager_views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('filemanager.urls')),
    path('accounts/', include('django.contrib.auth.urls')), # Встроенные URL-адреса аутентификации
    
]

# Только для разработки! В продакшене медиа обрабатываются внешним сервером
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)