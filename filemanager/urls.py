from django.urls import path
from . import views

urlpatterns = [
    # Главная и авторизация
    path('', views.home, name='home'),
    path('accounts/signup/', views.signup, name='signup'), 

    # Просмотр файлов (корень и вложенные папки)
    path('files/', views.my_files, name='my_files'), 
    path('files/<int:directory_id>/', views.my_files, name='my_files_in_dir'), 

    # Операции с контентом
    path('upload/', views.upload_file, name='upload_file'),
    path('create_folder/', views.create_directory, name='create_directory'),
    
    # Файловые действия
    path('download/<int:file_id>/', views.download_file, name='download_file'),
    path('delete/file/<int:file_id>/', views.delete_file, name='delete_file'),
    
    # Работа с папками
    path('delete/dir/<int:directory_id>/', views.delete_directory, name='delete_directory'),
    
    # Шаринг и публичный доступ
    path('share/<int:file_id>/', views.toggle_share, name='toggle_share'),
    path('public/download/<uuid:token>/', views.public_download, name='public_download'),
]