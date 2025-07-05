# myapp/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django import forms
import json

# Simple Forms
class SimpleRegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=30, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Confirm Password'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password != confirm_password:
            raise ValidationError("Passwords don't match")
        return cleaned_data

class SimpleLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

# Views
def register_view(request):
    """Simple user registration"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SimpleRegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password=form.cleaned_data['password']
            )
            
            # Auto login
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = SimpleRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    """Simple login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SimpleLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            remember_me = form.cleaned_data.get('remember_me')
            
            login(request, user)
            
            if not remember_me:
                request.session.set_expiry(0)
            
            messages.success(request, 'Login successful!')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
    else:
        form = SimpleLoginForm()
    
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    """Simple logout"""
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

@login_required
def profile_view(request):
    """Simple profile view"""
    return render(request, 'auth/profile.html', {'user': request.user})

@login_required
def edit_profile(request):
    """Simple profile edit"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'auth/edit_profile.html', {'user': request.user})