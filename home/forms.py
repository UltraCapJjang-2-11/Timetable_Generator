from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Student

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Student
        fields = ['student_id', 'email', 'password1', 'password2', 'department', 'year']