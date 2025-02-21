from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy


def login_view(request):
    return render(request, 'home/login.html')

def dashboard_view(request):
    return render(request, 'home/dashboard.html')

def timetable_view(request):
    return render(request, 'home/timetable.html')
