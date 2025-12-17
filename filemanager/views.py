import uuid
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import FileResponse, Http404, HttpResponseForbidden, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone

from cryptography.fernet import Fernet

from .models import UserFile, Directory
from .forms import FileUploadForm, DirectoryForm

# --- Общие страницы ---

def home(request):
    """Главная страница, куда попадают все по умолчанию"""
    return render(request, 'filemanager/home.html')

def signup(request):
    """Регистрация новых юзеров"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('my_files')
    else:
        form = UserCreationForm()
    return render(request, 'filemanager/signup.html', {'form': form})

# --- Работа с файловым менеджером ---

@login_required
def my_files(request, directory_id=None):
    """Основной вьювер файлов и папок"""
    current_directory = None
    breadcrumbs = []
    
    # Собираем путь для хлебных крошек, если мы внутри папки
    if directory_id:
        current_directory = get_object_or_404(Directory, id=directory_id, user=request.user)
        dir_chain = []
        d = current_directory
        while d is not None:
            dir_chain.append(d)
            d = d.parent
        dir_chain.reverse()
        breadcrumbs = dir_chain

    # Тянем контент текущей директории
    files_list = UserFile.objects.filter(user=request.user, directory=current_directory).order_by('filename')
    directories_list = Directory.objects.filter(user=request.user, parent=current_directory).order_by('name')

    # Если юзер что-то ищет через строку поиска
    search_query = request.GET.get('q')
    if search_query:
        files_list = files_list.filter(Q(filename__icontains=search_query))
        directories_list = directories_list.filter(Q(name__icontains=search_query))

    # Склеиваем папки и файлы для вывода списком
    contents = list(directories_list) + list(files_list)
    
    # Пагинация по 20 объектов на страницу
    paginator = Paginator(contents, 20) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'filemanager/my_files.html', {
        'page_obj': page_obj,
        'current_directory': current_directory,
        'breadcrumbs': breadcrumbs,
        'search_query': search_query,
        'upload_form': FileUploadForm(), 
    })

@login_required
def upload_file(request):
    """Прием и шифрование файла"""
    directory_id = request.POST.get('directory_id')
    current_directory = None
    
    if directory_id:
        current_directory = get_object_or_404(Directory, id=directory_id, user=request.user)

    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user
            uploaded_file.filename = uploaded_file.file.name
            uploaded_file.directory = current_directory
            
            # Логика шифрования через Fernet
            master_fernet = Fernet(settings.MASTER_ENCRYPTION_KEY)
            
            # Генерим уникальный ключ именно для этого файла
            file_key = Fernet.generate_key()
            file_fernet = Fernet(file_key)
            
            # Читаем байты, шифруем и подменяем контент перед сохранением
            file_data = request.FILES['file'].read()
            encrypted_data = file_fernet.encrypt(file_data)
            
            # Сам ключ файла храним зашифрованным мастер-ключом (безопасность!)
            uploaded_file.encryption_key = master_fernet.encrypt(file_key) 
            
            uploaded_file.file.save(
                uploaded_file.filename,
                ContentFile(encrypted_data)
            )
            uploaded_file.save()
            
            if current_directory:
                return redirect('my_files_in_dir', directory_id=current_directory.id)
            return redirect('my_files')
            
    return redirect('my_files')

@login_required
def create_directory(request):
    """Создание новой папки"""
    parent_id = request.GET.get('parent_id')
    parent_directory = None

    if parent_id:
        parent_directory = get_object_or_404(Directory, id=parent_id, user=request.user)

    if request.method == 'POST':
        form = DirectoryForm(request.POST)
        if form.is_valid():
            new_dir = form.save(commit=False)
            new_dir.user = request.user
            new_dir.parent = parent_directory
            try:
                new_dir.save()
                return redirect('my_files_in_dir', directory_id=new_dir.parent.id) if new_dir.parent else redirect('my_files')
            except Exception:
                form.add_error('name', 'Такая папка тут уже есть')
    else:
        form = DirectoryForm()

    return render(request, 'filemanager/create_directory.html', {'form': form, 'parent_directory': parent_directory})

# --- Удаление и шаринг ---

@login_required
def delete_file(request, file_id):
    """Удаление файла с подтверждением"""
    user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
    if request.method == 'POST':
        user_file.delete()
        return redirect('my_files')
    return render(request, 'filemanager/delete_file_confirm.html', {'user_file': user_file})

@login_required
def delete_directory(request, directory_id):
    """Удаление папки и всего содержимого"""
    dir_to_del = get_object_or_404(Directory, id=directory_id, user=request.user)
    parent_id = dir_to_del.parent_id 

    if request.method == 'POST':
        dir_to_del.delete()
        return redirect('my_files_in_dir', directory_id=parent_id) if parent_id else redirect('my_files')
        
    return render(request, 'filemanager/delete_directory_confirm.html', {'directory': dir_to_del})

@login_required
def toggle_share(request, file_id):
    """Управление публичной ссылкой (вкл/выкл на 24 часа)"""
    user_file = get_object_or_404(UserFile, id=file_id, user=request.user)

    if user_file.is_shared:
        user_file.is_shared = False
        user_file.share_token = None
        user_file.share_expires_at = None
    else:
        user_file.is_shared = True
        if not user_file.share_token:
             user_file.share_token = uuid.uuid4()
        user_file.share_expires_at = timezone.now() + timedelta(hours=24)
             
    user_file.save()
    return redirect('my_files_in_dir', directory_id=user_file.directory.id) if user_file.directory else redirect('my_files')

# --- Скачивание и дешифровка ---

@login_required
def download_file(request, file_id):
    """Скачивание файла владельцем (с дешифровкой)"""
    user_file = get_object_or_404(UserFile, id=file_id, user=request.user)
    try:
        master_fernet = Fernet(settings.MASTER_ENCRYPTION_KEY)
        # Достаем ключ файла и расшифровываем его мастер-ключом
        file_key = master_fernet.decrypt(user_file.encryption_key)
        file_fernet = Fernet(file_key)
        
        with user_file.file.open('rb') as f:
            decrypted_data = file_fernet.decrypt(f.read())

        response = HttpResponse(decrypted_data, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{user_file.filename}"'
        return response
    except Exception as e:
        return HttpResponseForbidden("Ошибка при расшифровке файла.")

def public_download(request, token):
    """Скачивание по публичной ссылке"""
    user_file = get_object_or_404(UserFile, share_token=token, is_shared=True)
    
    # Проверяем, актуальна ли ссылка
    if user_file.share_expires_at and user_file.share_expires_at < timezone.now():
        user_file.is_shared = False
        user_file.save()
        return HttpResponseForbidden("Срок действия ссылки истек.")
    
    try:
        master_fernet = Fernet(settings.MASTER_ENCRYPTION_KEY)
        # Если файл старый и без ключа — отдаем как есть
        if not user_file.encryption_key:
            response_data = user_file.file.read()
        else:
            file_key = master_fernet.decrypt(user_file.encryption_key)
            file_fernet = Fernet(file_key)
            with user_file.file.open('rb') as f:
                response_data = file_fernet.decrypt(f.read())

        response = HttpResponse(response_data, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{user_file.filename}"'
        return response
    except Exception:
        return HttpResponseForbidden("Файл поврежден или ключ не подходит.")