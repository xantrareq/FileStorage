# filemanager/forms.py
from django import forms
from .models import UserFile, Directory 

class FileUploadForm(forms.ModelForm):

    class Meta:
        model = UserFile
        fields = ('file',)


# НОВАЯ ФОРМА: Создание папки


class DirectoryForm(forms.ModelForm):
    class Meta:
        model = Directory
        fields = ('name',)
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Имя новой папки'}),
        }