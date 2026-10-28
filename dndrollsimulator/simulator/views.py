from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .models import *
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

def home(request):
    return render(request, 'registration/home.html')

class BootstrapAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control", "placeholder": field.label,})

def login_page(request):
    form = BootstrapAuthenticationForm(
        request=request,
        data=request.POST or None
    )

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('/home/')

        messages.error(request, "Invalid username or password.")

    return render(request, 'registration/login.html', {'form': form})


def register_page(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']

            form.save()

            messages.success(
                request,
                "Your account has been created successfully. Please log in."
            )
            return redirect('login')

        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = UserCreationForm()

    return render(
        request,
        'register.html',
        {'form': form}
    )


@login_required
def home(request):
    return render(request, 'registration/home.html')