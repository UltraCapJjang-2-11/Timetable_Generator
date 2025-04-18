from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="유효한 이메일을 입력하세요.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
