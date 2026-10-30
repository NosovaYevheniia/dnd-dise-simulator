import secrets

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django import forms
from .models import Character, DiceRoll, UserPreferences

User = get_user_model()


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = ["theme", "large_text", "reduce_motion"]
        widgets = {
            "theme": forms.Select(attrs={"class": "settings-input"}),
            "large_text": forms.CheckboxInput(attrs={
                "class": "settings-checkbox"
            }),
            "reduce_motion": forms.CheckboxInput(attrs={
                "class": "settings-checkbox"
            }),
        }


class UsernameSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username"]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "settings-input",
                "autocomplete": "username",
            }),
        }


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "settings-input"


CHARACTER_ABILITY_SCORE_FIELDS = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)


def home(request):
    return render(request, "home.html")

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

def dice_roller(request):
    return render(request, "dice.html")


def _roll_history_owner(request):
    if request.user.is_authenticated:
        return {"user": request.user, "session_key": None}

    if request.session.session_key is None:
        request.session.create()
    return {"user": None, "session_key": request.session.session_key}


@require_POST
def roll_dice(request):
    try:
        sides = int(request.POST.get("sides", ""))
        quantity = int(request.POST.get("quantity", ""))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Dice sides and quantity must be integers.")

    if sides not in {4, 6, 8, 10, 12, 20, 100}:
        return HttpResponseBadRequest("Unsupported die type.")
    if not 1 <= quantity <= 20:
        return HttpResponseBadRequest("Quantity must be between 1 and 20.")

    rolls = [secrets.randbelow(sides) + 1 for _ in range(quantity)]
    total = sum(rolls)
    roll = DiceRoll.objects.create(
        **_roll_history_owner(request),
        sides=sides,
        rolls=rolls,
        total=total,
    )

    return JsonResponse({
        "id": roll.pk,
        "sides": sides,
        "rolls": rolls,
        "total": total,
    })


def roll_history(request):
    owner = _roll_history_owner(request)
    rolls = DiceRoll.objects.filter(**owner)
    return render(request, "history.html", {"rolls": rolls})


def characters(request):
    all_characters = Character.objects.all().order_by("name")

    return render(request, "characters.html", {
        "characters": all_characters
    })


def character_search(request):
    query = request.GET.get("q", "").strip()

    results = Character.objects.all()

    if query:
        results = results.filter(
            Q(name__icontains=query) |
            Q(race__icontains=query) |
            Q(character_class__icontains=query)
        )

    results = results.order_by("name")

    return render(request, "_character_results.html", {
        "characters": results
    })



class CharacterForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = [
            "name",
            "race",
            "character_class",
            "level",
            *CHARACTER_ABILITY_SCORE_FIELDS,
            "image",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter character name"
            }),
            "race": forms.TextInput(attrs={
                "placeholder": "e.g. Elf, Human, Dwarf"
            }),
            "character_class": forms.TextInput(attrs={
                "placeholder": "e.g. Wizard, Fighter, Rogue"
            }),
            "level": forms.NumberInput(attrs={
                "min": 1,
                "max": 20
            }),
            "image": forms.ClearableFileInput(attrs={
                "accept": "image/*"
            }),
        }

        for ability in CHARACTER_ABILITY_SCORE_FIELDS:
            widgets[ability] = forms.NumberInput(attrs={
                "type": "range",
                "min": 3,
                "max": 18,
                "step": 1,
                "class": "ability-score-slider",
                "oninput": "this.nextElementSibling.value = this.value",
            })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for ability in CHARACTER_ABILITY_SCORE_FIELDS:
            self.fields[ability].min_value = 3
            self.fields[ability].max_value = 18
            self.fields[ability].widget.attrs.update({
                "min": 3,
                "max": 18,
            })

    def clean_level(self):
        level = self.cleaned_data["level"]

        if not 1 <= level <= 20:
            raise forms.ValidationError(
                "Level must be between 1 and 20."
            )

        return level

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image must be 5 MB or smaller.")

        return image


def create_character(request):
    if request.method == "POST":
        form = CharacterForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()

            response = HttpResponse("")
            response["HX-Trigger"] = "characterSaved"
            return response

    else:
        form = CharacterForm()

    return render(request, "character_form.html", {
        "form": form,
        "character": None,
    })


def edit_character(request, character_id):
    character = get_object_or_404(Character, pk=character_id)

    if request.method == "POST":
        form = CharacterForm(
            request.POST,
            request.FILES,
            instance=character,
        )

        if form.is_valid():
            form.save()

            response = HttpResponse("")
            response["HX-Trigger"] = "characterSaved"
            return response
    else:
        form = CharacterForm(instance=character)

    return render(request, "character_form.html", {
        "form": form,
        "character": character,
    })


@login_required(login_url="login_page")
def settings_page(request):
    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    preferences_form = UserPreferencesForm(instance=preferences)
    username_form = UsernameSettingsForm(instance=request.user)
    password_form = StyledPasswordChangeForm(request.user)

    if request.method == "POST":
        section = request.POST.get("section")

        if section == "appearance":
            preferences_form = UserPreferencesForm(
                request.POST,
                instance=preferences,
            )
            if preferences_form.is_valid():
                preferences_form.save()
                messages.success(request, "Appearance and accessibility saved.")
                return redirect("settings")

        elif section == "username":
            username_form = UsernameSettingsForm(
                request.POST,
                instance=request.user,
            )
            if username_form.is_valid():
                username_form.save()
                messages.success(request, "Username updated.")
                return redirect("settings")

        elif section == "password":
            password_form = StyledPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated.")
                return redirect("settings")

        else:
            return HttpResponseBadRequest("Unknown settings section.")

    return render(request, "settings.html", {
        "preferences_form": preferences_form,
        "username_form": username_form,
        "password_form": password_form,
    })


@login_required
def home(request):
    return render(request, 'registration/home.html')