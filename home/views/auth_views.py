"""
인증 관련 뷰들
로그인, 회원가입, 로그아웃 등의 사용자 인증 기능을 담당합니다.
"""

from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse_lazy
from ..forms import CustomUserCreationForm


class CustomLoginView(LoginView):
    """사용자 로그인 뷰"""
    template_name = 'home/login.html'
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # ?next= 우선, 없으면 대시보드로 이동
        return self.get_redirect_url() or reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 회원가입 폼이 없으면 추가
        if 'register_form' not in context:
            context['register_form'] = CustomUserCreationForm()
        return context


def signup(request):
    """사용자 회원가입 뷰"""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "회원가입이 완료되었습니다. 로그인 해주세요.")
            return redirect('login')
        else:
            messages.error(request, "회원가입 정보를 확인해주세요.")
    else:
        form = CustomUserCreationForm()

    login_form = AuthenticationForm()
    return render(request, 'home/login.html', {
        'signup_form': form,
        'login_form': login_form
    })


def logout_view(request):
    """사용자 로그아웃 뷰"""
    logout(request)
    return redirect('/') 