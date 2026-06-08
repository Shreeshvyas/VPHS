from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import User, ActivityLog
from .forms import ERPUserCreationForm, ERPUserUpdateForm
from .decorators import admin_only, super_admin_only, role_required
from .middleware import log_activity

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                log_activity(user, "LOGIN", {"status": "success"}, request)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request.user, "LOGOUT", {"status": "success"}, request)
        logout(request)
        messages.success(request, "You have been successfully logged out.")
    return redirect('login')

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        # Simulate sending reset email or print message
        messages.info(request, f"If an account is associated with {email}, password reset instructions have been sent. Please contact the Super Admin for direct password resets.")
        return render(request, 'users/forgot_password.html', {'success': True})
    return render(request, 'users/forgot_password.html')

@login_required
@admin_only
def user_list(request):
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.filter(is_deleted=False).order_by('-date_joined')
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(mobile__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)
        
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'roles': User.ROLE_CHOICES
    }
    return render(request, 'users/user_list.html', context)

@login_required
@admin_only
def user_create(request):
    if request.method == 'POST':
        form = ERPUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity(request.user, f"CREATE_USER", {"created_user": user.username, "role": user.role}, request)
            messages.success(request, f"User {user.username} successfully created.")
            return redirect('user_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ERPUserCreationForm()
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Create New User'})

@login_required
@admin_only
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = ERPUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            log_activity(request.user, f"UPDATE_USER", {"updated_user": user.username, "role": user.role}, request)
            messages.success(request, f"User {user.username} successfully updated.")
            return redirect('user_list')
        else:
            messages.error(request, "Please correct the errors.")
    else:
        form = ERPUserUpdateForm(instance=user)
    return render(request, 'users/user_form.html', {'form': form, 'title': f"Edit User: {user.username}"})

@login_required
@admin_only
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk, is_deleted=False)
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_list')
        
    if request.method == 'POST':
        user.delete()
        log_activity(request.user, f"DELETE_USER", {"deleted_user": user.username}, request)
        messages.success(request, f"User {user.username} successfully soft-deleted.")
        return redirect('user_list')
    return render(request, 'users/user_confirm_delete.html', {'user_obj': user})

@login_required
@super_admin_only
def activity_logs(request):
    query = request.GET.get('q', '')
    user_id = request.GET.get('user_id', '')
    
    logs = ActivityLog.objects.all().select_related('user')
    
    if query:
        logs = logs.filter(
            Q(action__icontains=query) |
            Q(ip_address__icontains=query) |
            Q(details__icontains=query)
        )
    if user_id:
        logs = logs.filter(user_id=user_id)
        
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'user_id': user_id,
        'users': User.objects.filter(is_deleted=False)
    }
    return render(request, 'users/activity_logs.html', context)
