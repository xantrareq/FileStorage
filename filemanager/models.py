import os
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings

# --- Вспомогательные функции ---

def user_directory_path(instance, filename):
    """
    Формирует путь: MEDIA_ROOT/user_<id>/dir_<id>/filename
    Если папки нет, кладем просто в корень юзера.
    """
    base_path = f'user_{instance.user.id}/'
    if instance.directory:
        return os.path.join(base_path, f'dir_{instance.directory.id}', filename)
    return os.path.join(base_path, filename)


# --- Модели ---

class Directory(models.Model):
    """Модель для имитации файловой структуры (папок)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Чтобы в одной директории не плодить одинаковые имена
        unique_together = ('user', 'name', 'parent')
        verbose_name_plural = "Directories"

    def __str__(self):
        return f"{self.user.username}: {self.name}"


class UserFile(models.Model):
    """Основная модель файла с поддержкой шифрования и шаринга"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    directory = models.ForeignKey(Directory, on_delete=models.CASCADE, null=True, blank=True)
    
    # Ключ файла (храним зашифрованным под мастер-ключом сервера)
    encryption_key = models.BinaryField(max_length=255)
    
    # Фактический файл и его метаданные
    file = models.FileField(upload_to=user_directory_path)
    filename = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)

    # Публичный доступ
    is_shared = models.BooleanField(default=False)
    share_token = models.UUIDField(unique=True, null=True, blank=True)
    share_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.filename} (owner: {self.user.username})"

    def delete(self, *args, **kwargs):
        """Переопределяем удаление, чтобы файлы не висели на диске"""
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)


# --- Сигналы для очистки хвостов ---

@receiver(post_delete, sender=UserFile)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """На случай, если файл удален каскадно или через админку"""
    if instance.file:
        instance.file.delete(save=False)


@receiver(post_delete, sender=Directory)
def cleanup_physical_directories(sender, instance, **kwargs):
    """
    После удаления записи о папке из БД, пытаемся удалить пустую папку на сервере.
    """
    # Путь к папке: user_<id>/dir_<id>
    dir_path = os.path.join(
        settings.MEDIA_ROOT, 
        f'user_{instance.user.id}', 
        f'dir_{instance.id}'
    )
    
    if os.path.exists(dir_path):
        try:
            # Удаляем саму папку (только если пуста)
            os.rmdir(dir_path)
            
            # Если папка юзера теперь тоже пустая, её удаляем
            user_root = os.path.join(settings.MEDIA_ROOT, f'user_{instance.user.id}')
            if os.path.exists(user_root) and not os.listdir(user_root):
                os.rmdir(user_root)
        except OSError:
            # Если там остались файлы (например, ручная загрузка), просто игнорим
            pass