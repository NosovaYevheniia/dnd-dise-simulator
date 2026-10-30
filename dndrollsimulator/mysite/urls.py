"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from simulator import views
from django.template.loader import get_template
from simulator.views import *
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda request: redirect('login_page')),
    path('admin/', admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path('login/', login_page, name='login_page'),
    path('register/', register_page, name='register'),
    path("home/", views.home, name="home"),
    path("dice/", views.dice_roller, name="dice_roller"),
    path("dice/roll/", views.roll_dice, name="roll_dice"),
    path("history/", views.roll_history, name="roll_history"),
    path("characters/", views.characters, name="characters"),
    path("settings/", views.settings_page, name="settings"),
    path("characters/search/", views.character_search, name="character_search"),
    path("characters/create/", views.create_character, name="create_character"),
    path(
        "characters/<int:character_id>/edit/",
        views.edit_character,
        name="edit_character",
    ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()