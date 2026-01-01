# events/auth_views.py (Create this new file)
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm

def admin_login(request):
    """Admin login page"""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        else:
            return redirect('event_list')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Check if user is staff/admin
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    messages.success(request, f'Welcome back, {username}!')
                    return redirect('admin_dashboard')
                else:
                    messages.error(request, 'You do not have admin privileges.')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'events/admin_login.html', {'form': form})

@login_required(login_url='admin_login')
def admin_logout(request):
    """Admin logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('event_list')

# Optional: User registration (if you want users to create accounts)
from django.contrib.auth.forms import UserCreationForm

def user_register(request):
    """User registration page"""
    if request.user.is_authenticated:
        return redirect('event_list')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('event_list')
    else:
        form = UserCreationForm()
    
    return render(request, 'events/register.html', {'form': form})