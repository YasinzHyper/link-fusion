from django.shortcuts import render, redirect
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.urls import reverse_lazy, reverse

from core.models import UserProfile


class SignupView(CreateView):
    form_class = UserCreationForm
    template_name = 'users/auth/signup.html'
    success_url = reverse_lazy('core:dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        # Create user profile
        UserProfile.objects.get_or_create(user=self.object)
        messages.success(self.request, 'Welcome to LinkFusion! Your account has been created.')
        return response


class CustomLoginView(LoginView):
    template_name = 'users/auth/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('core:dashboard')


class CustomLogoutView(LogoutView):
    template_name = 'users/auth/logout.html'
